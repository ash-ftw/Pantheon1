"""App Runtime & Container Lifecycle Service — PRD Module 4.

Manages runtime container execution, state synchronization, stop/start,
and resource cleanup for tenant applications.
"""

import asyncio
import socket
from typing import Any

from docker.errors import DockerException, NotFound
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models import App, AppVersion
from app.services.docker_builder import (
    docker_builder,
    sanitize_docker_image_tag,
    sanitize_docker_name,
)

logger = get_logger(__name__)

# Port range reserved for Pantheon tenant apps
_PORT_RANGE_START = 8085
_PORT_RANGE_END = 8200


def _get_ports_used_by_pantheon_containers() -> set[int]:
    """Query Docker for all host ports currently bound by ANY container."""
    used_ports: set[int] = set()
    try:
        client = docker_builder._get_client()
        if not client:
            return used_ports
        containers = client.containers.list(all=True)
        for c in containers:
            try:
                c.reload()
                if c.ports:
                    for _container_port, bindings in c.ports.items():
                        if bindings:
                            for binding in bindings:
                                hp = binding.get("HostPort")
                                if hp:
                                    used_ports.add(int(hp))
            except Exception:
                pass
    except Exception:
        pass
    return used_ports


def _is_port_free_on_host(port: int) -> bool:
    """Check if a TCP port is actually free on the host OS (not just Docker)."""
    # 1. Active connection probe — if connect succeeds, a service is actively listening
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        try:
            res = s.connect_ex(("127.0.0.1", port))
            if res == 0:
                return False
        except Exception:
            pass

    # 2. Exclusive bind probe
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def find_available_host_port(
    preferred_port: int = 8085, exclude_container: str | None = None
) -> int:
    """Find an available TCP port that is free on the host AND not used by other Pantheon containers.

    Args:
        preferred_port: The ideal port to try first (usually the container's internal port).
        exclude_container: Container name to exclude from the "in-use" check (useful when
                          recreating a container — its old binding shouldn't block itself).

    Returns:
        An available host port number.
    """
    # Gather ports already bound by other Pantheon app containers
    pantheon_ports = _get_ports_used_by_pantheon_containers()

    # If we're recreating a specific container, don't count its own port as occupied
    if exclude_container:
        try:
            client = docker_builder._get_client()
            if client:
                try:
                    c = client.containers.get(exclude_container)
                    c.reload()
                    if c.ports:
                        for _, bindings in c.ports.items():
                            if bindings:
                                for binding in bindings:
                                    hp = binding.get("HostPort")
                                    if hp:
                                        pantheon_ports.discard(int(hp))
                except NotFound:
                    pass
        except Exception:
            pass

    # Try preferred port first
    if preferred_port not in pantheon_ports and _is_port_free_on_host(preferred_port):
        return preferred_port

    # Scan the dedicated Pantheon port range
    for p in range(_PORT_RANGE_START, _PORT_RANGE_END):
        if p == preferred_port:
            continue
        if p in pantheon_ports:
            continue
        if _is_port_free_on_host(p):
            return p

    # Fallback: let the OS pick an ephemeral port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class AppRuntimeService:
    """Manages Docker container runtime state (start, stop, status sync, delete) for tenant apps."""

    def get_container_name(self, app_name: str) -> str:
        """Derive standard Docker container name from application name."""
        service_name = sanitize_docker_name(app_name)
        return f"pantheon-app-{service_name}"

    def _get_container_host_port(self, container_name: str) -> int | None:
        """Inspect a container and return its first host port binding, or None."""
        try:
            client = docker_builder._get_client()
            if not client:
                return None
            c = client.containers.get(container_name)
            c.reload()
            if c.ports:
                for _, bindings in c.ports.items():
                    if bindings:
                        hp = bindings[0].get("HostPort")
                        if hp:
                            return int(hp)
        except Exception:
            pass
        return None

    def is_container_running(self, app_name: str) -> bool:
        """Check if Docker container exists and is actively in 'running' state."""
        try:
            client = docker_builder._get_client()
            if not client:
                return False
            container_name = self.get_container_name(app_name)
            c = client.containers.get(container_name)
            c.reload()
            return c.status == "running"
        except (NotFound, DockerException, Exception):
            return False

    async def sync_app_status(self, app: App, db: AsyncSession) -> bool:
        """Sync app database status with actual Docker container status.

        Returns True if status changed and needs commit.
        """
        # Only synchronize runtime state if the app was previously built/running/stopped
        if app.status not in ("running", "stopped"):
            return False

        # If Docker daemon is unavailable, preserve current status without false transitions
        client = docker_builder._get_client()
        if not client:
            return False

        is_running = await asyncio.to_thread(self.is_container_running, app.name)
        new_status = "running" if is_running else "stopped"

        changed = False
        if app.status != new_status:
            logger.info(
                "syncing_app_runtime_status",
                app_id=str(app.id),
                app_name=app.name,
                old_status=app.status,
                new_status=new_status,
            )
            app.status = new_status
            changed = True

        # Also sync the host_port from the actual container bindings into target_profile
        if new_status == "running":
            container_name = self.get_container_name(app.name)
            actual_port = await asyncio.to_thread(self._get_container_host_port, container_name)
            if actual_port:
                tp = dict(app.target_profile) if app.target_profile else {}
                if tp.get("host_port") != actual_port:
                    tp["host_port"] = actual_port
                    app.target_profile = tp
                    changed = True

        if changed:
            db.add(app)

        return changed

    async def start_app(self, app: App, db: AsyncSession) -> dict[str, Any]:
        """Start the app's Docker container instance.

        If container already exists (e.g. exited), checks that its port binding
        is still available before starting. If the port is taken, recreates the
        container with a fresh port. After start, verifies the container is healthy.
        """
        container_name = self.get_container_name(app.name)
        client = docker_builder._get_client()

        if not client:
            # Fallback for mock/CI environments without Docker daemon
            app.status = "running"
            await db.commit()
            return {"status": "running", "container": container_name, "mode": "simulated"}

        # 1. Try starting existing container if found — but verify its port first
        try:
            c = await asyncio.to_thread(client.containers.get, container_name)
            if c.status != "running":
                # Check if the container's old host port is still free
                old_host_port = await asyncio.to_thread(
                    self._get_container_host_port, container_name
                )
                port_ok = True
                if old_host_port:
                    # Port might be taken by another container now
                    pantheon_ports = await asyncio.to_thread(_get_ports_used_by_pantheon_containers)
                    # Exclude our own container's port from the "used" set
                    pantheon_ports.discard(old_host_port)
                    if old_host_port in pantheon_ports or not _is_port_free_on_host(old_host_port):
                        port_ok = False
                        logger.info(
                            "container_old_port_conflict",
                            container=container_name,
                            old_port=old_host_port,
                        )

                if port_ok:
                    await asyncio.to_thread(c.start)
                    await asyncio.to_thread(c.reload)

                    if c.status == "running":
                        # Sync host_port into target_profile
                        actual_port = await asyncio.to_thread(
                            self._get_container_host_port, container_name
                        )
                        tp = dict(app.target_profile) if app.target_profile else {}
                        if actual_port:
                            tp["host_port"] = actual_port
                        app.target_profile = tp
                        app.status = "running"
                        await db.commit()
                        return {
                            "status": "running",
                            "container": container_name,
                            "state": c.status,
                            "host_port": actual_port,
                        }
                else:
                    # Port conflict — remove old container, will recreate below
                    logger.info("removing_container_for_port_rebind", container=container_name)
                    try:
                        await asyncio.to_thread(c.remove, force=True)
                    except Exception:
                        pass
        except NotFound:
            pass
        except Exception as e:
            logger.warning(
                "container_start_failed_retrying_recreate", container=container_name, error=str(e)
            )
            # Remove stale/failing container before recreating
            try:
                old_c = await asyncio.to_thread(client.containers.get, container_name)
                await asyncio.to_thread(old_c.remove, force=True)
            except Exception:
                pass

        # 2. Recreate container from latest image version
        res = await db.execute(
            select(AppVersion)
            .where(AppVersion.app_id == app.id)
            .order_by(AppVersion.version_number.desc())
        )
        ver = res.scalars().first()
        if not ver or not ver.image_tag:
            raise ValueError(
                "No built container image found for this application. Please redeploy first."
            )

        clean_tag = sanitize_docker_image_tag(ver.image_tag)
        current_image_tag = clean_tag
        if clean_tag != ver.image_tag:
            ver.image_tag = clean_tag
            await db.commit()

        container_port = 8085
        has_native_cmd = False
        img = None
        try:
            img = await asyncio.to_thread(client.images.get, current_image_tag)
        except Exception:
            img = None

        if img is None:
            # 1. Try pulling image from registry
            try:
                logger.info("pulling_missing_image_before_start", image=current_image_tag)
                await asyncio.to_thread(client.images.pull, current_image_tag)
                img = await asyncio.to_thread(client.images.get, current_image_tag)
            except Exception:
                img = None

        if img is None:
            # 2. Check if this is a known demo app or has demo workload
            from app.services.demo_workloads import match_demo_app_key, write_demo_files

            demo_key = match_demo_app_key(app.name, app.source_url)
            if demo_key:
                logger.info(
                    "building_demo_image_on_demand",
                    app=app.name,
                    demo_key=demo_key,
                    tag=current_image_tag,
                )
                import tempfile

                with tempfile.TemporaryDirectory() as td:
                    write_demo_files(demo_key, td)
                    await asyncio.to_thread(
                        docker_builder.build_image,
                        build_context=td,
                        image_tag=current_image_tag,
                    )
                try:
                    img = await asyncio.to_thread(client.images.get, current_image_tag)
                except Exception as get_err:
                    logger.warning("get_built_demo_image_failed", error=str(get_err))

        if img is None:
            # 3. Fuzzy check: if any locally built image matches this app name, tag it
            try:
                all_images = await asyncio.to_thread(client.images.list)
                app_token = app.name.lower().replace(" ", "-")
                for candidate in all_images:
                    tags = candidate.tags or []
                    for t in tags:
                        t_lower = t.lower()
                        if app_token in t_lower or ("app-" + app_token) in t_lower:
                            logger.info(
                                "re_tagging_matched_local_image",
                                matched_tag=t,
                                target_tag=current_image_tag,
                            )
                            await asyncio.to_thread(candidate.tag, current_image_tag)
                            img = await asyncio.to_thread(client.images.get, current_image_tag)
                            break
                    if img is not None:
                        break
            except Exception as match_err:
                logger.warning("fuzzy_image_match_failed", error=str(match_err))

        if img is None:
            raise ValueError(
                f"Container image '{current_image_tag}' was not found locally or in registry (localhost:5000). "
                "Please rebuild or redeploy the application."
            )

        has_explicit_exposed_port = False
        if img is not None:
            try:
                img_config = img.attrs.get("Config") or {}
                img_exposed = img_config.get("ExposedPorts") or {}
                if img_exposed:
                    for port_spec in img_exposed.keys():
                        port_num = int(port_spec.split("/")[0])
                        container_port = port_num
                        has_explicit_exposed_port = True
                        break

                cmd = img_config.get("Cmd")
                entrypoint = img_config.get("Entrypoint")
                if cmd and cmd != ["/bin/sh"]:
                    has_native_cmd = True
                elif entrypoint and entrypoint != ["/bin/sh", "-c"]:
                    has_native_cmd = True
            except Exception:
                pass

        if (
            not has_explicit_exposed_port
            and app.target_profile
            and "exposed_ports" in app.target_profile
        ):
            ports = app.target_profile.get("exposed_ports", [])
            if ports and isinstance(ports, list) and len(ports) > 0:
                p_val = ports[0]
                if isinstance(p_val, dict):
                    container_port = p_val.get("container_port", 8085)
                elif isinstance(p_val, int):
                    container_port = p_val

        host_port = find_available_host_port(container_port, exclude_container=container_name)

        # Clean up any stale container with the same name before recreating
        try:
            old_c = await asyncio.to_thread(client.containers.get, container_name)
            await asyncio.to_thread(old_c.remove, force=True)
        except Exception:
            pass

        # Build a robust CMD override — bypasses any broken CMD or node base image entrypoint
        # Includes zero-dependency Node.js static server as ultimate fallback when
        # `serve` is not installed and `npx serve` can't download (no internet in container).
        def _serve_fb(d: str, p: str = f"${{PORT:-{container_port}}}") -> str:
            return (
                f"(serve -s {d} -l {p} --cors 2>/dev/null "
                f"|| npx --yes serve -s {d} -l {p} --cors 2>/dev/null "
                f'|| node -e "'
                "const h=require('http'),f=require('fs'),p=require('path'),"
                f"P={p},R='{d}',"
                "M={{'.html':'text/html','.js':'application/javascript','.mjs':'application/javascript','.cjs':'application/javascript','.ts':'application/javascript','.tsx':'application/javascript','.jsx':'application/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml','.ico':'image/x-icon','.woff':'font/woff','.woff2':'font/woff2'}};"
                "h.createServer((q,r)=>{{r.setHeader('Access-Control-Allow-Origin','*');"
                "let u=p.join(R,decodeURIComponent(q.url.split('?')[0]));"
                "if(u.endsWith('/'))u=p.join(u,'index.html');"
                "f.stat(u,(e,s)=>{{if(e||!s.isFile()){{f.readFile(p.join(R,'index.html'),(e2,d)=>{{if(e2){{r.writeHead(404);r.end('Not found');return}}r.writeHead(200,{{'Content-Type':'text/html'}});r.end(d)}});return}}"
                "r.writeHead(200,{{'Content-Type':M[p.extname(u).toLowerCase()]||'application/octet-stream'}});f.createReadStream(u).pipe(r)}})}})"
                f".listen(P,'0.0.0.0',()=>console.log('Pantheon static server on port '+P))"
                '")'
            )

        fallback_cmd = (
            "if [ ! -d dist ] && [ ! -d build ] && [ -f package.json ] && grep -q '\"build\"' package.json 2>/dev/null; then "
            "(npm run build 2>/dev/null || npx vite build 2>/dev/null || true); fi; "
            "JS_ENTRY=$(find . -maxdepth 5 -type f \\( -name index.js -o -name main.js -o -name server.js -o -name app.js \\) 2>/dev/null | grep '/dist/' | grep -v '/node_modules/' | grep -v '/packages/' | grep -v '/assets/' | head -n 1); "
            "HTML_ENTRY=$(find . -maxdepth 5 -type f -name index.html 2>/dev/null | grep '/dist/' | grep -v '/node_modules/' | head -n 1); "
            "if [ -f package.json ] && grep -q '\"start\"' package.json; then exec npm start; "
            'elif [ -n "$JS_ENTRY" ]; then echo "Starting Node backend: $JS_ENTRY" && exec node "$JS_ENTRY"; '
            "elif [ -f dist/index.html ]; then " + _serve_fb("dist") + "; "
            "elif [ -f dist/client/index.html ]; then " + _serve_fb("dist/client") + "; "
            'elif [ -n "$HTML_ENTRY" ]; then HTML_DIR=$(dirname "$HTML_ENTRY") && echo "Serving static frontend: $HTML_DIR" && '
            + _serve_fb('"$HTML_DIR"')
            + "; "
            "elif [ -f build/index.html ]; then " + _serve_fb("build") + "; "
            "elif [ -d .next ]; then npm start -- -p ${PORT:-8085} -H 0.0.0.0 || npx next start -p ${PORT:-8085} -H 0.0.0.0; "
            "elif [ -f server.js ]; then exec node server.js; "
            "elif [ -f index.js ]; then exec node index.js; "
            "elif [ -f app.js ]; then exec node app.js; "
            "elif [ -f main.js ]; then exec node main.js; "
            "elif [ -f main.py ]; then exec python main.py; "
            "elif [ -f app.py ]; then exec python app.py; "
            "elif [ -f manage.py ]; then exec python manage.py runserver 0.0.0.0:${PORT:-8085}; "
            "elif [ -f package.json ] && grep -q '\"preview\"' package.json; then (exec bun run preview --host 0.0.0.0 --port ${PORT:-8085} 2>/dev/null || exec npm run preview -- --host 0.0.0.0 --port ${PORT:-8085}); "
            "elif [ -f package.json ] && grep -q '\"dev\"' package.json; then (exec bun run dev --host 0.0.0.0 --port ${PORT:-8085} 2>/dev/null || exec npm run dev -- --host 0.0.0.0 --port ${PORT:-8085}); "
            "else " + _serve_fb(".") + "; fi"
        )

        def _run_container():
            kwargs: dict[str, Any] = {
                "image": current_image_tag,
                "name": container_name,
                "detach": True,
                "ports": {f"{container_port}/tcp": host_port},
                "environment": {
                    "PORT": str(container_port),
                    "HOST": "0.0.0.0",
                    "CLIENT_ORIGIN": "http://localhost:5173",
                },
            }
            if not has_native_cmd:
                kwargs["entrypoint"] = ""
                kwargs["command"] = ["/bin/sh", "-c", fallback_cmd]
            return client.containers.run(**kwargs)

        c = await asyncio.to_thread(_run_container)

        # Verify the container actually started — poll for up to 8 seconds
        # (some containers need time to install packages via npx, etc.)
        container_alive = False
        for _attempt in range(8):
            await asyncio.sleep(1)
            await asyncio.to_thread(c.reload)
            if c.status == "running":
                container_alive = True
                break
            elif c.status in ("exited", "dead"):
                break  # No point waiting further

        if not container_alive:
            # Container exited — capture logs for diagnostics
            try:
                logs_tail = c.logs(tail=30).decode("utf-8", errors="replace")
            except Exception:
                logs_tail = "(unable to read logs)"
            logger.error(
                "container_exited_after_start",
                container=container_name,
                status=c.status,
                logs=logs_tail,
            )
            app.status = "failed"
            await db.commit()
            raise ValueError(
                f"Container started but exited (status: {c.status}). Logs:\n{logs_tail}"
            )

        app.status = "running"
        # Always save host_port, even if target_profile was previously None
        tp = dict(app.target_profile) if app.target_profile else {}
        tp["host_port"] = host_port
        app.target_profile = tp
        await db.commit()
        return {
            "status": "running",
            "container": container_name,
            "state": "running",
            "host_port": host_port,
        }

    async def stop_app(self, app: App, db: AsyncSession) -> dict[str, Any]:
        """Stop the application's Docker container instance."""
        container_name = self.get_container_name(app.name)
        client = docker_builder._get_client()

        if client:
            try:
                c = await asyncio.to_thread(client.containers.get, container_name)
                await asyncio.to_thread(c.stop, timeout=2)
            except Exception as e:
                logger.info("container_stop_note", container=container_name, error=str(e))

        app.status = "stopped"
        await db.commit()
        return {"status": "stopped", "container": container_name}

    async def delete_app_resources(self, app_name: str) -> None:
        """Clean up Docker container when deleting an application."""
        container_name = self.get_container_name(app_name)
        client = docker_builder._get_client()
        if client:
            try:
                c = await asyncio.to_thread(client.containers.get, container_name)
                try:
                    await asyncio.to_thread(c.stop, timeout=2)
                except Exception:
                    pass
                await asyncio.to_thread(c.remove, force=True)
            except Exception:
                pass


app_runtime_service = AppRuntimeService()
