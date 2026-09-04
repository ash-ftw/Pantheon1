"""Phase 10 Attack Graph Test Suite — PRD Module 12 / Module 9.

Tests:
1. AttackGraphNode and AttackGraphEdge model persistence in PostgreSQL.
2. Simulation Engine builds graph with nodes (Attacker, Route, Endpoint) and edges.
3. Node color-coding and status transitions (probing, safe, blocked, compromised).
4. Replay timeline metadata: step_discovered for step-by-step filtering.
5. REST endpoints: GET /api/attack-graph/runs, GET /api/attack-graph/{id}, GET /api/test-runs/{id}/graph.
6. Kill switch updates Route Broker node status to blocked.
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.database import async_session_factory
from app.main import app
from app.models import (
    App,
    AttackGraphEdge,
    AttackGraphNode,
    Org,
    TestRun,
    User,
)
from app.services.auth_service import create_access_token
from app.services.simulation_engine import simulation_engine

DUMMY_HASH = "$2b$12$dummyhashedpasswordvaluefortestingpurpose"


@pytest.mark.asyncio
async def test_attack_graph_models_and_persistence() -> None:
    """Verify AttackGraphNode and AttackGraphEdge can be created and queried in PostgreSQL."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()
    run_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="Graph Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        app_obj = App(
            id=app_id,
            org_id=org_id,
            name="Graph Target App",
            source_type="git",
            source_url="https://github.com/example/target.git",
            status="running",
            target_profile={"exposed_ports": [8085]},
        )
        session.add(app_obj)
        await session.commit()

        run = TestRun(
            id=run_id,
            org_id=org_id,
            app_id=app_id,
            scenario_name="OWASP SQL Injection Suite",
            scenario_category="sqli_resilience",
            status="completed",
            total_steps=3,
            current_step=3,
            metrics={},
            logs=[],
        )
        session.add(run)
        await session.commit()

        node1 = AttackGraphNode(
            id=uuid.uuid4(),
            org_id=org_id,
            test_run_id=run_id,
            node_id="attacker",
            label="Range Attacker Pod",
            node_type="attacker",
            status="safe",
            step_discovered=0,
            position_x=80.0,
            position_y=200.0,
            metadata_json={"cluster": "range"},
        )
        node2 = AttackGraphNode(
            id=uuid.uuid4(),
            org_id=org_id,
            test_run_id=run_id,
            node_id="route_broker",
            label="Route Broker Ingress",
            node_type="route",
            status="safe",
            step_discovered=0,
            position_x=320.0,
            position_y=200.0,
            metadata_json={"ttl": 1800},
        )
        edge1 = AttackGraphEdge(
            id=uuid.uuid4(),
            test_run_id=run_id,
            edge_id="attacker->route",
            source_node_id="attacker",
            target_node_id="route_broker",
            label="Ephemeral Ingress",
            status="traversed",
            step_discovered=0,
            metadata_json={},
        )
        session.add_all([node1, node2, edge1])
        await session.commit()

        # Retrieve and assert
        graph_data = await simulation_engine.get_test_run_graph(run_id, db=session)
        assert graph_data["test_run_id"] == str(run_id)
        assert len(graph_data["nodes"]) >= 2
        assert len(graph_data["edges"]) >= 1

        node_ids = [n["id"] for n in graph_data["nodes"]]
        assert "attacker" in node_ids
        assert "route_broker" in node_ids

        edge_ids = [e["id"] for e in graph_data["edges"]]
        assert "attacker->route" in edge_ids


@pytest.mark.asyncio
async def test_get_test_run_graph_service_fallback() -> None:
    """Verify get_test_run_graph synthesizes graph nodes for older test runs."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()
    run_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="Fallback Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        app_obj = App(
            id=app_id,
            org_id=org_id,
            name="Target App",
            source_type="git",
            source_url="https://github.com/example/target.git",
            status="running",
            target_profile={"exposed_ports": [8085]},
        )
        session.add(app_obj)
        await session.commit()

        run = TestRun(
            id=run_id,
            org_id=org_id,
            app_id=app_id,
            scenario_name="API Abuse & Rate Limit Probe",
            scenario_category="api_abuse",
            status="completed",
            total_steps=2,
            current_step=2,
            metrics={},
            logs=[],
        )
        session.add(run)
        await session.commit()

        # Call get_test_run_graph without prior nodes
        graph_data = await simulation_engine.get_test_run_graph(run_id, db=session)
        assert len(graph_data["nodes"]) >= 3  # attacker + route + step nodes
        assert len(graph_data["edges"]) >= 2

        # Check step_discovered ordering
        step_discovered_vals = [n["step_discovered"] for n in graph_data["nodes"]]
        assert 0 in step_discovered_vals
        assert 1 in step_discovered_vals


@pytest.mark.asyncio
async def test_attack_graph_rest_endpoints() -> None:
    """Verify REST endpoints for listing graph runs and fetching graph data."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()
    user_id = uuid.uuid4()
    run_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="REST Graph Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        user = User(
            id=user_id,
            email=f"graph-user-{uuid.uuid4().hex[:6]}@example.com",
            full_name="Graph Operator",
            hashed_password=DUMMY_HASH,
            org_id=org_id,
            role="Admin",
            is_active=True,
        )
        session.add(user)
        await session.commit()

        app_obj = App(
            id=app_id,
            org_id=org_id,
            name="REST Target",
            source_type="git",
            source_url="https://github.com/example/target.git",
            status="running",
            target_profile={"exposed_ports": [8085]},
        )
        session.add(app_obj)
        await session.commit()

        run = TestRun(
            id=run_id,
            org_id=org_id,
            app_id=app_id,
            scenario_name="Authentication Header Bypass Probe",
            scenario_category="auth_abuse",
            status="completed",
            total_steps=3,
            current_step=3,
            metrics={"requests_sent": 30},
            logs=[],
        )
        session.add(run)
        await session.commit()

    token = create_access_token(user_id=user_id, email=user.email, org_id=org_id, role="Admin")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List runs available for attack graph
        runs_res = await client.get("/api/attack-graph/runs", headers=headers)
        assert runs_res.status_code == 200
        runs_data = runs_res.json()
        assert len(runs_data) > 0
        matched = next((r for r in runs_data if r["id"] == str(run_id)), None)
        assert matched is not None
        assert "node_count" in matched
        assert "edge_count" in matched

        # 2. Get attack graph via /api/attack-graph/{id}
        graph_res = await client.get(f"/api/attack-graph/{run_id}", headers=headers)
        assert graph_res.status_code == 200
        graph_data = graph_res.json()
        assert graph_data["test_run_id"] == str(run_id)
        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert len(graph_data["nodes"]) >= 2

        # 3. Get attack graph via /api/test-runs/{id}/graph alias
        alias_res = await client.get(f"/api/test-runs/{run_id}/graph", headers=headers)
        assert alias_res.status_code == 200
        assert alias_res.json()["test_run_id"] == str(run_id)


@pytest.mark.asyncio
async def test_kill_switch_attack_graph_block() -> None:
    """Verify emergency stop sets route node status to blocked in attack graph."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()
    run_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="Kill Graph Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        app_obj = App(
            id=app_id,
            org_id=org_id,
            name="Kill App",
            source_type="git",
            source_url="https://github.com/example/target.git",
            status="running",
            target_profile={"exposed_ports": [8085]},
        )
        session.add(app_obj)
        await session.commit()

        run = TestRun(
            id=run_id,
            org_id=org_id,
            app_id=app_id,
            scenario_name="Emergency Stop Probe",
            scenario_category="api_abuse",
            status="running",
            total_steps=4,
            current_step=1,
            metrics={},
            logs=[],
        )
        session.add(run)
        await session.commit()

        # Add initial route node in safe state
        route_node = AttackGraphNode(
            id=uuid.uuid4(),
            org_id=org_id,
            test_run_id=run_id,
            node_id="route_broker",
            label="Route Broker Ingress (/r/test-route)",
            node_type="route",
            status="safe",
            step_discovered=0,
            position_x=320.0,
            position_y=200.0,
            metadata_json={},
        )
        session.add(route_node)
        await session.commit()

        # Trigger emergency stop
        stopped = await simulation_engine.stop_test_run(
            run_id=run_id,
            reason="Operator Kill Switch Test",
            org_id=org_id,
            db=session,
        )
        assert stopped["status"] == "stopped"

        # Check graph route node status
        graph = await simulation_engine.get_test_run_graph(run_id, db=session)
        route_in_graph = next((n for n in graph["nodes"] if n["id"] == "route_broker"), None)
        assert route_in_graph is not None
        assert route_in_graph["status"] == "blocked"
        assert "REVOKED" in route_in_graph["label"]
