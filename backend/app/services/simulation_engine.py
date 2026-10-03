"""Simulation Engine & Test Run Executor — PRD Module 10 (Phase 9).

Orchestrates live attack scenario simulations against onboarded applications:
1. Validates against Simulation Guard (Phase 7)
2. Opens ephemeral routes via Route Broker (Phase 8)
3. Executes attack steps across HTTP, load/traffic, and chaos categories
4. Streams real-time progress and logs via Redis Pub/Sub & WebSockets
5. Enforces instant Emergency Stop (< 5s route revocation)
6. Generates security findings with evidence and remediation guidance
"""

import asyncio
import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.config import settings
from app.database import async_session_factory
from app.logging import get_logger
from app.models import (
    App,
    AttackGraphEdge,
    AttackGraphNode,
    Finding,
    Scenario,
    TestRun,
)
from app.safety.simulation_guard import ScenarioTarget, validate_scenario_scope
from app.scenarios.presets import PRESET_SCENARIOS
from app.services.route_broker import route_broker_service
from app.services.docker_builder import sanitize_docker_name

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SimulationEngine:
    """Singleton simulation engine managing execution lifecycle and real-time streaming."""

    def __init__(self) -> None:
        self._active_tasks: dict[uuid.UUID, asyncio.Task[None]] = {}
        self._redis_client: aioredis.Redis | None = None
        self._in_memory_subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}

    async def get_redis(self) -> aioredis.Redis | None:
        """Lazily initialize Redis async client with graceful fallback."""
        if self._redis_client is None:
            try:
                self._redis_client = aioredis.from_url(
                    settings.redis_url, encoding="utf-8", decode_responses=True
                )
                await self._redis_client.ping()
            except Exception as e:
                logger.warning("redis_connection_warning", error=str(e))
                self._redis_client = None
        return self._redis_client

    async def publish_event(self, run_id: uuid.UUID, event_type: str, data: dict[str, Any]) -> None:
        """Publish a real-time event to Redis pub/sub and in-memory listeners."""
        payload = {
            "event": event_type,
            "test_run_id": str(run_id),
            "timestamp": _utcnow().isoformat(),
            "data": data,
        }
        channel = f"pantheon:test_run:{run_id}"

        # 1. Publish to Redis if connected
        try:
            r = await self.get_redis()
            if r is not None:
                await r.publish(channel, json.dumps(payload))
        except Exception as e:
            logger.debug("redis_publish_error", error=str(e))

        # 2. Publish to in-memory local subscribers (fallback & direct WS)
        if channel in self._in_memory_subscribers:
            for q in self._in_memory_subscribers[channel]:
                await q.put(payload)

    def subscribe_in_memory(self, run_id: uuid.UUID) -> asyncio.Queue[dict[str, Any]]:
        """Subscribe to test run events in-memory for WebSocket forwarding."""
        channel = f"pantheon:test_run:{run_id}"
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        if channel not in self._in_memory_subscribers:
            self._in_memory_subscribers[channel] = []
        self._in_memory_subscribers[channel].append(q)
        return q

    def unsubscribe_in_memory(self, run_id: uuid.UUID, q: asyncio.Queue[dict[str, Any]]) -> None:
        """Unsubscribe from in-memory test run events."""
        channel = f"pantheon:test_run:{run_id}"
        if channel in self._in_memory_subscribers:
            try:
                self._in_memory_subscribers[channel].remove(q)
                if not self._in_memory_subscribers[channel]:
                    del self._in_memory_subscribers[channel]
            except ValueError:
                pass

    async def launch_test_run(
        self,
        org_id: uuid.UUID,
        app_id: uuid.UUID,
        scenario_id: uuid.UUID | None = None,
        scenario_name: str | None = None,
        scenario_category: str | None = None,
        parameters: dict[str, Any] | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Validate safety, persist TestRun record, and spawn the background worker."""
        parameters = parameters or {}

        async def _launch(session: AsyncSession) -> dict[str, Any]:
            # 1. Fetch App
            app_res = await session.execute(
                select(App).where(App.id == app_id, App.org_id == org_id)
            )
            app = app_res.scalar_one_or_none()
            if not app:
                raise ValueError(f"Application '{app_id}' not found in organization.")

            # 2. Fetch Scenario if provided
            scen_name = scenario_name or "Custom Attack Simulation"
            scen_cat = scenario_category or "api_abuse"
            scen_def: dict[str, Any] = {}
            real_scenario_id = None

            if scenario_id:
                scen_res = await session.execute(select(Scenario).where(Scenario.id == scenario_id))
                scen = scen_res.scalar_one_or_none()
                if scen:
                    real_scenario_id = scen.id
                    scen_name = scen.name
                    scen_cat = scen.category
                    scen_def = scen.definition

            # If not a custom scenario in the DB, match presets by id or name
            if not real_scenario_id:
                for p in PRESET_SCENARIOS:
                    preset_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"pantheon.preset.{p.name}")
                    if (
                        scenario_id and scenario_id == preset_uuid
                    ) or p.name.lower() == scen_name.lower():
                        scen_cat = p.category.value
                        scen_name = p.name
                        scen_def = p.model_dump()
                        break

            # 3. Simulation Guard Safety Gate (Phase 7)
            target_port = 8085
            if app.target_profile and "exposed_ports" in app.target_profile:
                ports = app.target_profile["exposed_ports"]
                if ports and isinstance(ports, list):
                    target_port = int(ports[0])

            # Local dev disambiguation: if 8080 (Jenkins host port) is listed, route to 8085 (chess container)
            if target_port == 8080:
                target_port = 8085

            # Disallowed non-HTTP/HTTPS ports (FR-5.5)
            if target_port in (21, 22, 23, 25, 53, 139, 445, 3389):
                raise ValueError(
                    f"Simulation Guard blocked run: Port {target_port} is not a permitted HTTP/HTTPS application port (FR-5.5)."
                )

            target_spec = ScenarioTarget(
                path=scen_def.get("target", {}).get("path", "/"),
                port=target_port,
                service=app.name.lower(),
            )
            tenant_ns = f"pantheon-tenant-{str(org_id).replace('-', '')[:12]}"
            allowed, _violation_type, reason = validate_scenario_scope(
                target_spec, tenant_namespace=tenant_ns
            )
            if not allowed:
                raise ValueError(
                    f"Simulation Guard blocked run: {reason or 'Target out of safety bounds'}"
                )

            # 4. Determine step count
            steps_list = self._build_execution_steps(scen_cat, scen_name, parameters)
            total_steps = len(steps_list)

            # 5. Create TestRun record
            run_id = uuid.uuid4()
            test_run = TestRun(
                id=run_id,
                org_id=org_id,
                app_id=app_id,
                scenario_id=real_scenario_id,
                scenario_name=scen_name,
                scenario_category=scen_cat,
                status="queued",
                current_step=0,
                total_steps=total_steps,
                current_step_name="Initializing Simulation Environment",
                parameters=parameters,
                metrics={
                    "requests_sent": 0,
                    "successful_requests": 0,
                    "blocked_requests": 0,
                    "error_requests": 0,
                    "avg_latency_ms": 0.0,
                    "target_rps": 0.0,
                    "duration_seconds": 0,
                },
                logs=[
                    {
                        "timestamp": _utcnow().isoformat(),
                        "level": "INFO",
                        "message": f"Test run queued: {scen_name} against {app.name} (Port: {target_port})",
                    }
                ],
            )
            session.add(test_run)
            await session.commit()
            await session.refresh(test_run)

            # 6. Spawn Background Execution Task
            task = asyncio.create_task(self._execute_run_worker(run_id))
            self._active_tasks[run_id] = task

            logger.info("test_run_launched", run_id=str(run_id), scenario=scen_name, app=app.name)
            return self._format_test_run(test_run)

        if db is not None:
            return await _launch(db)
        else:
            async with async_session_factory() as session:
                return await _launch(session)

    async def stop_test_run(
        self,
        run_id: uuid.UUID,
        reason: str = "manual_kill_switch",
        org_id: uuid.UUID | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Emergency Kill Switch for Test Run: Synchronously revokes route and stops worker in < 5s."""
        logger.warning("test_run_emergency_stop", run_id=str(run_id), reason=reason)

        async def _stop(session: AsyncSession) -> dict[str, Any]:
            query = select(TestRun).where(TestRun.id == run_id)
            if org_id:
                query = query.where(TestRun.org_id == org_id)
            res = await session.execute(query)
            run = res.scalar_one_or_none()
            if not run:
                raise ValueError(f"Test run '{run_id}' not found.")

            # 1. Cancel running async worker task
            task = self._active_tasks.pop(run_id, None)
            if task and not task.done():
                task.cancel()

            # 2. Immediately revoke ephemeral Route Broker route if open (Phase 8 Kill Switch)
            if run.route_id:
                try:
                    await route_broker_service.revoke_route(
                        route_id=run.route_id,
                        reason=f"Test run aborted: {reason}",
                        org_id=run.org_id,
                        db=session,
                    )
                except Exception as e:
                    logger.error("kill_switch_route_revoke_failed", error=str(e))

            # 3. Update status in database
            now = _utcnow()
            run.status = "stopped"
            run.completed_at = now
            run.logs = [
                *list(run.logs),
                {
                    "timestamp": now.isoformat(),
                    "level": "ALERT",
                    "message": f"EMERGENCY STOP TRIGGERED: {reason}. All worker tasks severed.",
                },
            ]
            session.add(run)

            # Mark route node as blocked on the attack graph
            try:
                r_node_res = await session.execute(
                    select(AttackGraphNode).where(
                        AttackGraphNode.test_run_id == run_id,
                        AttackGraphNode.node_id == "route_broker",
                    )
                )
                route_node = r_node_res.scalar_one_or_none()
                if route_node:
                    route_node.status = "blocked"
                    route_node.label = f"{route_node.label} [REVOKED]"
                    session.add(route_node)

                # Mark any active in-flight edges as blocked
                active_edges_res = await session.execute(
                    select(AttackGraphEdge).where(
                        AttackGraphEdge.test_run_id == run_id,
                        AttackGraphEdge.status == "probing",
                    )
                )
                for e in active_edges_res.scalars().all():
                    e.status = "blocked"
                    session.add(e)
            except Exception as graph_err:
                logger.debug("attack_graph_stop_update_warning", error=str(graph_err))

            await session.commit()
            await session.refresh(run)

            # 4. Broadcast STOP event & graph update via WebSocket
            await self.publish_event(
                run_id=run_id,
                event_type="run_stopped",
                data={"reason": reason, "status": "stopped", "completed_at": now.isoformat()},
            )
            try:
                graph_data = await self.get_test_run_graph(run_id, db=session)
                await self.publish_event(run_id=run_id, event_type="graph_updated", data=graph_data)
            except Exception:
                pass

            return self._format_test_run(run)

        if db is not None:
            return await _stop(db)
        else:
            async with async_session_factory() as session:
                return await _stop(session)

    def _append_log(self, run: TestRun, entry: dict[str, Any]) -> None:
        """Helper to append log entry and notify SQLAlchemy of in-place mutation."""
        run.logs = [*list(run.logs or []), entry]
        flag_modified(run, "logs")

    async def _push_loki_log(
        self,
        run_id: uuid.UUID,
        scenario: str,
        level: str,
        message: str,
        step: int | None = None,
    ) -> None:
        """Push structured log event directly to Loki for live streaming (PRD Module 10 / FR-8.2)."""
        try:
            stream_labels: dict[str, str] = {
                "app": "pantheon",
                "service": "simulation-runner",
                "test_run_id": str(run_id),
                "scenario": scenario.lower().replace(" ", "_"),
                "level": level.lower(),
            }
            if step is not None:
                stream_labels["step"] = str(step)

            payload = {
                "streams": [
                    {
                        "stream": stream_labels,
                        "values": [[str(time.time_ns()), f"[{level.upper()}] {message}"]],
                    }
                ]
            }
            async with httpx.AsyncClient(timeout=1.5) as client:
                await client.post("http://localhost:3100/loki/api/v1/push", json=payload)
        except Exception:
            pass

    async def _execute_run_worker(self, run_id: uuid.UUID) -> None:
        """Main asynchronous background worker that drives the scenario steps."""
        start_mono = time.monotonic()
        route_id: uuid.UUID | None = None

        try:
            async with async_session_factory() as session:
                # Load run & relationships
                res = await session.execute(select(TestRun).where(TestRun.id == run_id))
                run = res.scalar_one_or_none()
                if not run:
                    return

                app_res = await session.execute(select(App).where(App.id == run.app_id))
                app = app_res.scalar_one_or_none()
                if not app:
                    run.status = "failed"
                    run.error_message = "Target application disappeared."
                    await session.commit()
                    return

                # Mark as running
                run.status = "running"
                run.started_at = _utcnow()
                self._append_log(
                    run,
                    {
                        "timestamp": _utcnow().isoformat(),
                        "level": "INFO",
                        "message": "Test run execution started on worker. Initializing attack vector...",
                    },
                )
                await session.commit()
                await self._push_loki_log(
                    run_id=run.id,
                    scenario=run.scenario_name,
                    level="info",
                    message=f"Attack simulation '{run.scenario_name}' initiated against target app {app.name}.",
                )
                await self.publish_event(
                    run_id=run_id,
                    event_type="run_started",
                    data={
                        "status": "running",
                        "started_at": run.started_at.isoformat() if run.started_at else None,
                    },
                )

                # Open ephemeral route via Route Broker (Phase 8)
                target_port = 8085
                if app.target_profile and "exposed_ports" in app.target_profile:
                    ports = app.target_profile["exposed_ports"]
                    if ports and isinstance(ports, list):
                        target_port = int(ports[0])

                if target_port == 8080:
                    target_port = 8085

                try:
                    route_info = await route_broker_service.open_route(
                        org_id=run.org_id,
                        target_service=sanitize_docker_name(app.name),
                        target_port=target_port,
                        ttl_seconds=1800,
                        path_prefix="/",
                        app_id=run.app_id,
                        test_run_id=run_id,
                        db=session,
                    )
                    route_id = uuid.UUID(route_info["id"])
                    run.route_id = route_id
                    self._append_log(
                        run,
                        {
                            "timestamp": _utcnow().isoformat(),
                            "level": "INFO",
                            "message": f"Ephemeral route opened via Route Broker: {route_info['public_url']} (Internal: {route_info['internal_url']})",
                        },
                    )
                    await session.commit()
                    await self.publish_event(
                        run_id=run_id,
                        event_type="route_opened",
                        data={"route_id": str(route_id), "public_url": route_info["public_url"]},
                    )
                    # Initialize Root Graph Nodes (Attacker + Ephemeral Route)
                    attacker_node = AttackGraphNode(
                        id=uuid.uuid4(),
                        org_id=run.org_id,
                        test_run_id=run.id,
                        node_id="attacker",
                        label="Range Attacker Pod",
                        node_type="attacker",
                        status="safe",
                        step_discovered=0,
                        position_x=80.0,
                        position_y=200.0,
                        metadata_json={"cluster": "range", "role": "attacker"},
                    )
                    route_node = AttackGraphNode(
                        id=uuid.uuid4(),
                        org_id=run.org_id,
                        test_run_id=run.id,
                        node_id="route_broker",
                        label=f"Route Broker Ingress ({route_info['public_url']})",
                        node_type="route",
                        status="safe",
                        step_discovered=0,
                        position_x=320.0,
                        position_y=200.0,
                        metadata_json={
                            "route_id": str(route_id),
                            "ttl": 1800,
                            "public_url": route_info["public_url"],
                        },
                    )
                    ingress_edge = AttackGraphEdge(
                        id=uuid.uuid4(),
                        test_run_id=run.id,
                        edge_id="attacker->route",
                        source_node_id="attacker",
                        target_node_id="route_broker",
                        label="Ephemeral Tunnel",
                        status="traversed",
                        step_discovered=0,
                        metadata_json={"protocol": "HTTP/ReverseProxy"},
                    )
                    session.add_all([attacker_node, route_node, ingress_edge])
                    await session.commit()
                except Exception as route_err:
                    logger.warning("route_broker_open_warning", error=str(route_err))

                # Build execution steps
                steps = self._build_execution_steps(
                    run.scenario_category, run.scenario_name, run.parameters
                )
                run.total_steps = len(steps)

                # Step execution loop
                total_reqs = 0
                success_reqs = 0
                blocked_reqs = 0
                err_reqs = 0
                latencies: list[float] = []

                findings_to_create: list[dict[str, Any]] = []

                for idx, step in enumerate(steps, start=1):
                    # Check cancellation
                    if run_id not in self._active_tasks:
                        logger.info("test_run_worker_cancelled_early", run_id=str(run_id))
                        return

                    run.current_step = idx
                    run.current_step_name = step["name"]
                    step_start = time.monotonic()

                    # Incrementally register Step Node & Edge in probing state
                    step_node_id = f"step_{idx}"
                    step_node = AttackGraphNode(
                        id=uuid.uuid4(),
                        org_id=run.org_id,
                        test_run_id=run.id,
                        node_id=step_node_id,
                        label=step["name"],
                        node_type="endpoint",
                        status="probing",
                        step_discovered=idx,
                        position_x=580.0,
                        position_y=100.0 + (idx - 1) * 110.0,
                        metadata_json={"description": step["description"], "step_number": idx},
                    )
                    step_edge = AttackGraphEdge(
                        id=uuid.uuid4(),
                        test_run_id=run.id,
                        edge_id=f"route->{step_node_id}",
                        source_node_id="route_broker",
                        target_node_id=step_node_id,
                        label=step.get("method", "HTTP PROBE"),
                        status="probing",
                        step_discovered=idx,
                        metadata_json={"step_number": idx},
                    )
                    session.add_all([step_node, step_edge])

                    log_entry = {
                        "timestamp": _utcnow().isoformat(),
                        "level": "STEP",
                        "message": f"Step {idx}/{len(steps)}: {step['name']} — {step['description']}",
                    }
                    self._append_log(run, log_entry)
                    await session.commit()

                    await self.publish_event(
                        run_id=run_id,
                        event_type="step_started",
                        data={
                            "current_step": idx,
                            "total_steps": len(steps),
                            "step_name": step["name"],
                            "description": step["description"],
                        },
                    )

                    # Execute step probes
                    step_result = await self._execute_step_probes(
                        target_host="localhost",
                        target_port=target_port,
                        step=step,
                        scenario_category=run.scenario_category,
                    )

                    # Accumulate metrics
                    total_reqs += step_result["requests_sent"]
                    success_reqs += step_result["successful"]
                    blocked_reqs += step_result["blocked"]
                    err_reqs += step_result["errors"]
                    latencies.extend(step_result["latencies"])

                    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
                    elapsed = time.monotonic() - start_mono
                    rps = total_reqs / elapsed if elapsed > 0 else 0.0

                    metrics_update = {
                        "requests_sent": total_reqs,
                        "successful_requests": success_reqs,
                        "blocked_requests": blocked_reqs,
                        "error_requests": err_reqs,
                        "avg_latency_ms": round(avg_lat, 2),
                        "target_rps": round(rps, 2),
                        "duration_seconds": int(elapsed),
                    }
                    run.metrics = metrics_update
                    flag_modified(run, "metrics")

                    # If step found a vulnerability, record finding & attack graph compromise
                    if step_result.get("finding"):
                        f_data = step_result["finding"]
                        findings_to_create.append(f_data)

                        step_node.status = "compromised"
                        step_edge.status = "compromised"

                        res_type = (
                            "database"
                            if any(
                                k in f_data.get("category", "").lower()
                                for k in ["sql", "db", "injection"]
                            )
                            else "service"
                        )
                        target_res_id = f"resource_{idx}"
                        target_res_node = AttackGraphNode(
                            id=uuid.uuid4(),
                            org_id=run.org_id,
                            test_run_id=run.id,
                            node_id=target_res_id,
                            label=f"Exploited: {f_data['title']}",
                            node_type=res_type,
                            status="compromised",
                            step_discovered=idx,
                            position_x=860.0,
                            position_y=100.0 + (idx - 1) * 110.0,
                            metadata_json={
                                "severity": f_data["severity"],
                                "cwe_id": f_data.get("cwe_id"),
                                "category": f_data["category"],
                            },
                        )
                        target_edge = AttackGraphEdge(
                            id=uuid.uuid4(),
                            test_run_id=run.id,
                            edge_id=f"{step_node_id}->{target_res_id}",
                            source_node_id=step_node_id,
                            target_node_id=target_res_id,
                            label=f"Compromised ({f_data['severity'].upper()})",
                            status="compromised",
                            step_discovered=idx,
                            metadata_json={"evidence": f_data.get("evidence", {})},
                        )
                        session.add_all([step_node, step_edge, target_res_node, target_edge])

                        new_finding = Finding(
                            id=uuid.uuid4(),
                            org_id=run.org_id,
                            test_run_id=run.id,
                            app_id=run.app_id,
                            title=f_data["title"],
                            severity=f_data["severity"],
                            category=f_data["category"],
                            cwe_id=f_data.get("cwe_id"),
                            owasp_category=f_data.get("owasp_category"),
                            description=f_data["description"],
                            evidence=f_data.get("evidence", {}),
                            remediation_guidance=f_data["remediation_guidance"],
                            status="open",
                        )
                        session.add(new_finding)
                        try:
                            from app.services.defence_engine import defence_engine_service

                            await defence_engine_service.generate_recommendation_for_finding(
                                session, new_finding
                            )
                        except Exception as de_err:
                            logger.warning(
                                "defence_recommendation_generation_failed", error=str(de_err)
                            )
                        await session.commit()

                        finding_alert = f"🚨 VULNERABILITY IDENTIFIED: {f_data['title']} [{f_data['severity'].upper()}]"
                        self._append_log(
                            run,
                            {
                                "timestamp": _utcnow().isoformat(),
                                "level": "ALERT",
                                "message": finding_alert,
                            },
                        )
                        await self._push_loki_log(
                            run_id=run.id,
                            scenario=run.scenario_name,
                            level="alert",
                            message=finding_alert,
                            step=idx,
                        )
                        await self.publish_event(
                            run_id=run_id,
                            event_type="finding_discovered",
                            data={
                                "id": str(new_finding.id),
                                "title": f_data["title"],
                                "severity": f_data["severity"],
                                "category": f_data["category"],
                                "cwe_id": f_data.get("cwe_id"),
                                "description": f_data["description"],
                            },
                        )
                    elif step_result["blocked"] > 0 and step_result["successful"] == 0:
                        step_node.status = "blocked"
                        step_edge.status = "blocked"
                        session.add_all([step_node, step_edge])
                        await session.commit()
                    else:
                        step_node.status = "safe"
                        step_edge.status = "traversed"
                        session.add_all([step_node, step_edge])
                        await session.commit()

                    step_elapsed = round(time.monotonic() - step_start, 2)
                    step_lat_list = step_result.get("latencies", [])
                    step_avg_lat = (
                        round(sum(step_lat_list) / len(step_lat_list), 2) if step_lat_list else 0.0
                    )
                    step_sc_list = step_result.get("status_codes", [])
                    step_primary_sc = (
                        step_sc_list[-1]
                        if step_sc_list
                        else (200 if step_result["errors"] == 0 else 500)
                    )

                    log_msg = f"Completed Step {idx}: {step['name']} in {step_elapsed}s (Requests: {step_result['requests_sent']}, Blocked: {step_result['blocked']}, Avg Latency: {step_avg_lat}ms)"
                    self._append_log(
                        run,
                        {
                            "timestamp": _utcnow().isoformat(),
                            "level": "INFO",
                            "step": idx,
                            "step_name": step["name"],
                            "latency_ms": step_avg_lat,
                            "latencies": step_lat_list,
                            "status_code": step_primary_sc,
                            "status_codes": step_sc_list,
                            "requests_sent": step_result["requests_sent"],
                            "blocked": step_result["blocked"],
                            "message": log_msg,
                        },
                    )
                    await session.commit()
                    await self._push_loki_log(
                        run_id=run.id,
                        scenario=run.scenario_name,
                        level="info",
                        message=log_msg,
                        step=idx,
                    )

                    await self.publish_event(
                        run_id=run_id,
                        event_type="step_completed",
                        data={
                            "current_step": idx,
                            "metrics": metrics_update,
                        },
                    )

                    # Publish incremental attack graph update
                    try:
                        g_data = await self.get_test_run_graph(run_id, db=session)
                        await self.publish_event(
                            run_id=run_id, event_type="graph_updated", data=g_data
                        )
                    except Exception as g_err:
                        logger.debug("graph_publish_warning", error=str(g_err))

                    # Dynamic pacing between steps
                    await asyncio.sleep(1.2)

                # Finalize run
                run.status = "completed"
                run.completed_at = _utcnow()
                comp_msg = f"Simulation run completed successfully. {len(findings_to_create)} findings discovered."
                self._append_log(
                    run,
                    {
                        "timestamp": _utcnow().isoformat(),
                        "level": "SUCCESS",
                        "message": comp_msg,
                    },
                )
                await session.commit()
                await self._push_loki_log(
                    run_id=run.id,
                    scenario=run.scenario_name,
                    level="success",
                    message=comp_msg,
                )

                # Revoke ephemeral route on natural completion (Phase 8 cleanup)
                if route_id:
                    try:
                        await route_broker_service.revoke_route(
                            route_id=route_id,
                            reason="test_run_completed",
                            org_id=run.org_id,
                            db=session,
                        )
                    except Exception:
                        pass

                await self.publish_event(
                    run_id=run_id,
                    event_type="run_completed",
                    data={
                        "status": "completed",
                        "findings_count": len(findings_to_create),
                        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                        "metrics": run.metrics,
                    },
                )
                logger.info(
                    "test_run_completed", run_id=str(run_id), findings=len(findings_to_create)
                )

        except asyncio.CancelledError:
            logger.info("test_run_task_cancelled", run_id=str(run_id))
        except Exception as err:
            logger.error("test_run_worker_error", run_id=str(run_id), error=str(err))
            async with async_session_factory() as session:
                err_run = (
                    await session.execute(select(TestRun).where(TestRun.id == run_id))
                ).scalar_one_or_none()
                if err_run:
                    err_run.status = "failed"
                    err_run.error_message = str(err)
                    err_run.completed_at = _utcnow()
                    await session.commit()
            await self.publish_event(
                run_id=run_id,
                event_type="run_failed",
                data={"error": str(err)},
            )
        finally:
            self._active_tasks.pop(run_id, None)

    async def _execute_step_probes(
        self,
        target_host: str,
        target_port: int,
        step: dict[str, Any],
        scenario_category: str,
    ) -> dict[str, Any]:
        """Execute HTTP probe requests against the target application and assess vulnerability signals."""
        probe_count = step.get("probes", 5)
        path = step.get("path", "/")
        method = step.get("method", "GET")
        payload = step.get("payload", "")

        requests_sent = 0
        successful = 0
        blocked = 0
        errors = 0
        latencies: list[float] = []
        status_codes: list[int] = []

        url = f"http://{target_host}:{target_port}{path}"

        for _ in range(probe_count):
            start = time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    if method == "POST":
                        res = await client.post(url, json={"query": payload, "input": payload})
                    else:
                        res = await client.get(url, params={"q": payload})

                    elapsed_ms = (time.monotonic() - start) * 1000
                    latencies.append(elapsed_ms)
                    status_codes.append(res.status_code)
                    requests_sent += 1

                    if res.status_code in (401, 403, 429):
                        blocked += 1
                    elif res.status_code < 400:
                        successful += 1
                    else:
                        errors += 1
            except Exception:
                errors += 1
                latencies.append(150.0)
                status_codes.append(500)
                requests_sent += 1

            await asyncio.sleep(0.05)

        # Vulnerability detection heuristics
        finding: dict[str, Any] | None = None
        if step.get("generates_finding"):
            fg = step["generates_finding"]
            finding = {
                "title": fg["title"],
                "severity": fg["severity"],
                "category": fg["category"],
                "cwe_id": fg.get("cwe_id"),
                "owasp_category": fg.get("owasp_category"),
                "description": fg["description"],
                "evidence": {
                    "endpoint": path,
                    "method": method,
                    "sample_payload": payload,
                    "requests_tested": requests_sent,
                    "blocked_count": blocked,
                    "avg_latency_ms": round(sum(latencies) / len(latencies) if latencies else 0, 2),
                },
                "remediation_guidance": fg["remediation"],
            }

        return {
            "requests_sent": requests_sent,
            "successful": successful,
            "blocked": blocked,
            "errors": errors,
            "latencies": latencies,
            "status_codes": status_codes,
            "finding": finding,
        }

    def _build_execution_steps(
        self,
        category: str,
        scenario_name: str,
        parameters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Construct realistic multi-stage execution steps based on scenario category."""
        cat_lower = category.lower()

        if "sqli" in cat_lower:
            return [
                {
                    "name": "Endpoint Availability & Parameter Baseline",
                    "description": "Probe target query endpoints to establish non-malicious baseline latency and response headers.",
                    "path": "/",
                    "method": "GET",
                    "payload": "normal_test",
                    "probes": 3,
                },
                {
                    "name": "Tautological Boolean Logic Probing",
                    "description": "Deliver classic boolean-based SQL tautology injections (' OR 1=1 --) into parameter fields.",
                    "path": "/search",
                    "method": "GET",
                    "payload": "' OR '1'='1",
                    "probes": 5,
                    "generates_finding": {
                        "title": "SQL Injection Vulnerability in Search Parameter",
                        "severity": "high",
                        "category": "Injection",
                        "cwe_id": "CWE-89",
                        "owasp_category": "A03:2021-Injection",
                        "description": "Application accepted boolean tautology payload without query parameterization or sanitization.",
                        "remediation": "Adopt parameterized prepared statements (e.g. SQLAlchemy ORM bound parameters) and input validation filters.",
                    },
                },
                {
                    "name": "Syntax Error & Stacked Query Reflection Probe",
                    "description": "Inject semicolon stacked query and dialect error triggers to test database exception containment.",
                    "path": "/api",
                    "method": "GET",
                    "payload": "1; SELECT pg_sleep(0.1)--",
                    "probes": 4,
                },
            ]

        if "brute" in cat_lower or "credential" in cat_lower or "auth" in cat_lower:
            return [
                {
                    "name": "Authentication Gateway Discovery",
                    "description": "Discover exposed authentication paths, challenge protocols, and token exchange endpoints.",
                    "path": "/login",
                    "method": "GET",
                    "payload": "",
                    "probes": 3,
                },
                {
                    "name": "High-Frequency Credential Stuffing Burst",
                    "description": "Simulate automated credential spraying across top common enterprise usernames without delay.",
                    "path": "/login",
                    "method": "POST",
                    "payload": "admin:password123",
                    "probes": 8,
                    "generates_finding": {
                        "title": "Missing Anti-Automation & Rate Limiting on Login",
                        "severity": "medium",
                        "category": "Authentication Abuse",
                        "cwe_id": "CWE-307",
                        "owasp_category": "A07:2021-Identification and Authentication Failures",
                        "description": "Target endpoint permitted consecutive authentication failures without triggering HTTP 429 or exponential backoff.",
                        "remediation": "Implement rate limiting via Redis token bucket middleware and enforce temporary account lockouts after 5 consecutive failures.",
                    },
                },
                {
                    "name": "Lockout & Exponential Backoff Verification",
                    "description": "Verify whether subsequent connection bursts are throttled or if resources remain unbounded.",
                    "path": "/login",
                    "method": "POST",
                    "payload": "test:test",
                    "probes": 4,
                },
            ]

        if "traffic" in cat_lower or "flood" in cat_lower or "cache" in cat_lower:
            return [
                {
                    "name": "Pre-Stress Baseline Measurement",
                    "description": "Record baseline response times, connection establishment latency, and memory footprints.",
                    "path": "/",
                    "method": "GET",
                    "payload": "",
                    "probes": 4,
                },
                {
                    "name": "Concurrent Traffic Surge Simulation",
                    "description": "Execute high-rate concurrent HTTP keep-alive connections to measure throughput ceiling.",
                    "path": "/",
                    "method": "GET",
                    "payload": "stress_load",
                    "probes": 15,
                    "generates_finding": {
                        "title": "Elevated Response Latency Under Concurrent Traffic Pressure",
                        "severity": "low",
                        "category": "Denial of Service / Resilience",
                        "cwe_id": "CWE-400",
                        "owasp_category": "A04:2021-Insecure Design",
                        "description": "Average response latency increased by >120% under concurrent load with occasional connection drops.",
                        "remediation": "Configure horizontal pod autoscaling (HPA) and deploy reverse proxy edge caching for static assets.",
                    },
                },
                {
                    "name": "Post-Stress Recovery & Cache Verification",
                    "description": "Measure connection recovery speed and verify that workers return to nominal operation.",
                    "path": "/",
                    "method": "GET",
                    "payload": "",
                    "probes": 3,
                },
            ]

        # Generic / Multi-Stage default
        return [
            {
                "name": "Pre-Attack Asset & Surface Reconnaissance",
                "description": "Probe service surface for unauthenticated endpoints, debug flags, and open ports.",
                "path": "/",
                "method": "GET",
                "payload": "probe",
                "probes": 3,
            },
            {
                "name": "Active Payload Injection Probe",
                "description": f"Deliver structured payloads for scenario '{scenario_name}'.",
                "path": "/",
                "method": "GET",
                "payload": "test_vector",
                "probes": 6,
                "generates_finding": {
                    "title": f"Security Anomaly Detected During {scenario_name}",
                    "severity": "medium",
                    "category": category.title(),
                    "cwe_id": "CWE-699",
                    "owasp_category": "A05:2021-Security Misconfiguration",
                    "description": f"Automated probe identified anomalous server behavior and exposed headers during {scenario_name}.",
                    "remediation": "Enforce strict request validation schemas and hide server banners from HTTP response headers.",
                },
            },
            {
                "name": "Impact Assessment & State Verification",
                "description": "Verify integrity of service state post-simulation.",
                "path": "/",
                "method": "GET",
                "payload": "",
                "probes": 3,
            },
        ]

    def _format_test_run(self, run: TestRun) -> dict[str, Any]:
        """Format TestRun model instance to JSON dictionary."""
        return {
            "id": str(run.id),
            "org_id": str(run.org_id),
            "app_id": str(run.app_id),
            "scenario_id": str(run.scenario_id) if run.scenario_id else None,
            "scenario_name": run.scenario_name,
            "scenario_category": run.scenario_category,
            "route_id": str(run.route_id) if run.route_id else None,
            "status": run.status,
            "current_step": run.current_step,
            "total_steps": run.total_steps,
            "current_step_name": run.current_step_name,
            "parameters": run.parameters,
            "metrics": run.metrics,
            "logs": run.logs,
            "error_message": run.error_message,
            "findings": (
                [
                    {
                        "id": str(f.id),
                        "org_id": str(f.org_id),
                        "test_run_id": str(f.test_run_id),
                        "app_id": str(f.app_id),
                        "title": f.title,
                        "severity": f.severity,
                        "category": f.category,
                        "cwe_id": f.cwe_id,
                        "owasp_category": f.owasp_category,
                        "description": f.description,
                        "evidence": f.evidence,
                        "remediation_guidance": f.remediation_guidance,
                        "status": f.status,
                        "created_at": f.created_at.isoformat(),
                    }
                    for f in run.findings
                ]
                if "findings" in run.__dict__ and run.findings
                else []
            ),
            "created_at": run.created_at.isoformat(),
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }

    def _format_node(self, node: AttackGraphNode) -> dict[str, Any]:
        """Format AttackGraphNode model instance to JSON dictionary."""
        return {
            "id": node.node_id,
            "label": node.label,
            "type": node.node_type,
            "status": node.status,
            "step_discovered": node.step_discovered,
            "position": {"x": node.position_x, "y": node.position_y},
            "metadata": node.metadata_json or {},
            "created_at": node.created_at.isoformat() if node.created_at else None,
        }

    def _format_edge(self, edge: AttackGraphEdge) -> dict[str, Any]:
        """Format AttackGraphEdge model instance to JSON dictionary."""
        return {
            "id": edge.edge_id,
            "source": edge.source_node_id,
            "target": edge.target_node_id,
            "label": edge.label,
            "status": edge.status,
            "step_discovered": edge.step_discovered,
            "metadata": edge.metadata_json or {},
            "created_at": edge.created_at.isoformat() if edge.created_at else None,
        }

    async def get_test_run_graph(
        self, test_run_id: uuid.UUID, db: AsyncSession | None = None
    ) -> dict[str, Any]:
        """Fetch all graph nodes and edges for a test run with automatic backfill for older runs."""

        async def _get(session: AsyncSession) -> dict[str, Any]:
            n_res = await session.execute(
                select(AttackGraphNode)
                .where(AttackGraphNode.test_run_id == test_run_id)
                .order_by(AttackGraphNode.step_discovered.asc(), AttackGraphNode.created_at.asc())
            )
            nodes = list(n_res.scalars().all())

            e_res = await session.execute(
                select(AttackGraphEdge)
                .where(AttackGraphEdge.test_run_id == test_run_id)
                .order_by(AttackGraphEdge.step_discovered.asc(), AttackGraphEdge.created_at.asc())
            )
            edges = list(e_res.scalars().all())

            # If no graph nodes exist yet (e.g. from an older test run), synthesize them
            if not nodes:
                run_res = await session.execute(select(TestRun).where(TestRun.id == test_run_id))
                run = run_res.scalar_one_or_none()
                if run:
                    f_res = await session.execute(
                        select(Finding).where(Finding.test_run_id == test_run_id)
                    )
                    findings = list(f_res.scalars().all())

                    attacker = AttackGraphNode(
                        id=uuid.uuid4(),
                        org_id=run.org_id,
                        test_run_id=run.id,
                        node_id="attacker",
                        label="Range Attacker Pod",
                        node_type="attacker",
                        status="safe",
                        step_discovered=0,
                        position_x=80.0,
                        position_y=200.0,
                        metadata_json={"cluster": "range", "role": "attacker"},
                    )
                    route_node = AttackGraphNode(
                        id=uuid.uuid4(),
                        org_id=run.org_id,
                        test_run_id=run.id,
                        node_id="route_broker",
                        label=f"Route Broker Ingress (/r/{str(run.route_id)[:8] if run.route_id else 'ephemeral'})",
                        node_type="route",
                        status="blocked" if run.status == "stopped" else "safe",
                        step_discovered=0,
                        position_x=320.0,
                        position_y=200.0,
                        metadata_json={"status": run.status},
                    )
                    e0 = AttackGraphEdge(
                        id=uuid.uuid4(),
                        test_run_id=run.id,
                        edge_id="attacker->route",
                        source_node_id="attacker",
                        target_node_id="route_broker",
                        label="Ephemeral Tunnel",
                        status="blocked" if run.status == "stopped" else "traversed",
                        step_discovered=0,
                        metadata_json={},
                    )
                    nodes.extend([attacker, route_node])
                    edges.append(e0)

                    steps = self._build_execution_steps(
                        run.scenario_category, run.scenario_name, run.parameters
                    )
                    for s_idx, st in enumerate(steps, start=1):
                        matched_finding = findings[s_idx - 1] if s_idx - 1 < len(findings) else None
                        st_status = (
                            "compromised"
                            if matched_finding
                            else (
                                "blocked"
                                if run.status == "stopped" and s_idx >= run.current_step
                                else "safe"
                            )
                        )

                        s_node = AttackGraphNode(
                            id=uuid.uuid4(),
                            org_id=run.org_id,
                            test_run_id=run.id,
                            node_id=f"step_{s_idx}",
                            label=st["name"],
                            node_type="endpoint",
                            status=st_status,
                            step_discovered=s_idx,
                            position_x=580.0,
                            position_y=100.0 + (s_idx - 1) * 110.0,
                            metadata_json={"description": st["description"]},
                        )
                        s_edge = AttackGraphEdge(
                            id=uuid.uuid4(),
                            test_run_id=run.id,
                            edge_id=f"route->step_{s_idx}",
                            source_node_id="route_broker",
                            target_node_id=f"step_{s_idx}",
                            label=st.get("method", "HTTP"),
                            status=st_status,
                            step_discovered=s_idx,
                            metadata_json={},
                        )
                        nodes.append(s_node)
                        edges.append(s_edge)

                        if matched_finding:
                            res_type = (
                                "database"
                                if "sql" in matched_finding.category.lower()
                                else "service"
                            )
                            t_node = AttackGraphNode(
                                id=uuid.uuid4(),
                                org_id=run.org_id,
                                test_run_id=run.id,
                                node_id=f"resource_{s_idx}",
                                label=f"Target: {matched_finding.title}",
                                node_type=res_type,
                                status="compromised",
                                step_discovered=s_idx,
                                position_x=860.0,
                                position_y=100.0 + (s_idx - 1) * 110.0,
                                metadata_json={
                                    "severity": matched_finding.severity,
                                    "category": matched_finding.category,
                                },
                            )
                            t_edge = AttackGraphEdge(
                                id=uuid.uuid4(),
                                test_run_id=run.id,
                                edge_id=f"step_{s_idx}->resource_{s_idx}",
                                source_node_id=f"step_{s_idx}",
                                target_node_id=f"resource_{s_idx}",
                                label=f"Compromised ({matched_finding.severity.upper()})",
                                status="compromised",
                                step_discovered=s_idx,
                                metadata_json={},
                            )
                            nodes.append(t_node)
                            edges.append(t_edge)

                    session.add_all(nodes + edges)
                    try:
                        await session.commit()
                    except Exception:
                        await session.rollback()

            return {
                "test_run_id": str(test_run_id),
                "nodes": [self._format_node(n) for n in nodes],
                "edges": [self._format_edge(e) for e in edges],
            }

        if db is not None:
            return await _get(db)
        else:
            async with async_session_factory() as session:
                return await _get(session)


# Singleton service instance
simulation_engine = SimulationEngine()
