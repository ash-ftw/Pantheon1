"""MinIO S3 & Docker Registry Storage Service.

Provides management and cleanup of Docker image repositories, layer blobs,
and build/report artifacts stored inside MinIO S3 object storage
(buckets: 'pantheon-registry' and 'pantheon-artifacts').
"""

import asyncio
from typing import Any

import httpx

from app.config import settings
from app.logging import get_logger
from app.services.docker_builder import docker_builder, sanitize_docker_name

logger = get_logger(__name__)


class MinioStorageService:
    """Manages Docker image storage in MinIO and local Docker daemon."""

    def __init__(self) -> None:
        self.registry_bucket = "pantheon-registry"
        self.artifacts_bucket = settings.minio_bucket or "pantheon-artifacts"
        self.registry_url = f"http://{settings.registry_url}"

    def _get_docker_client(self) -> Any:
        """Helper to get Docker client via docker_builder."""
        return docker_builder._get_client()

    def _exec_in_minio(self, cmd: str) -> tuple[int, str]:
        """Execute an mc command inside the pantheon-minio container."""
        client = self._get_docker_client()
        if not client:
            return -1, "Docker daemon unavailable"
        try:
            c = client.containers.get("pantheon-minio")
            # Ensure alias exists
            init_cmd = (
                "mc alias set myminio http://localhost:9000 minioadmin minioadmin > /dev/null 2>&1; "
                f"{cmd}"
            )
            res = c.exec_run(["/bin/sh", "-c", init_cmd])
            output = res.output.decode("utf-8", errors="replace") if res.output else ""
            return res.exit_code, output
        except Exception as e:
            logger.warning("minio_exec_error", error=str(e), cmd=cmd)
            return -1, str(e)

    def _exec_in_registry(self, cmd: list[str]) -> tuple[int, str]:
        """Execute garbage collection or admin command inside pantheon-registry container."""
        client = self._get_docker_client()
        if not client:
            return -1, "Docker daemon unavailable"
        try:
            c = client.containers.get("pantheon-registry")
            res = c.exec_run(cmd)
            output = res.output.decode("utf-8", errors="replace") if res.output else ""
            return res.exit_code, output
        except Exception as e:
            logger.warning("registry_exec_error", error=str(e), cmd=cmd)
            return -1, str(e)

    async def list_repositories(self, active_app_names: set[str] | None = None) -> list[dict[str, Any]]:
        """List all image repositories stored in Registry v2 / MinIO with metadata."""
        repos: list[str] = []

        # 1. Fetch catalog from Registry v2 API
        try:
            async with httpx.AsyncClient(timeout=5.0) as http_client:
                resp = await http_client.get(f"{self.registry_url}/v2/_catalog")
                if resp.status_code == 200:
                    repos = resp.json().get("repositories", [])
        except Exception as e:
            logger.info("registry_catalog_fetch_fallback", error=str(e))

        # Fallback / augment by inspecting MinIO directly if registry returned empty
        if not repos:
            exit_code, output = await asyncio.to_thread(
                self._exec_in_minio,
                f"mc ls myminio/{self.registry_bucket}/docker/registry/v2/repositories/",
            )
            if exit_code == 0:
                for line in output.splitlines():
                    line = line.strip()
                    if line:
                        parts = line.split()
                        folder = parts[-1].rstrip("/")
                        if folder:
                            # Subfolder might be org-id
                            sub_code, sub_out = await asyncio.to_thread(
                                self._exec_in_minio,
                                f"mc ls myminio/{self.registry_bucket}/docker/registry/v2/repositories/{folder}/",
                            )
                            if sub_code == 0 and sub_out.strip():
                                for sub_line in sub_out.splitlines():
                                    sub_parts = sub_line.strip().split()
                                    if sub_parts:
                                        app_folder = sub_parts[-1].rstrip("/")
                                        repos.append(f"{folder}/{app_folder}")
                            else:
                                repos.append(folder)

        results: list[dict[str, Any]] = []
        for repo_path in sorted(repos):
            parts = repo_path.split("/")
            org_id = parts[0] if len(parts) > 1 else ""
            repo_name = parts[-1]
            clean_app_name = repo_name.removeprefix("app-")

            # Fetch tags
            tags: list[str] = []
            try:
                async with httpx.AsyncClient(timeout=3.0) as http_client:
                    t_resp = await http_client.get(f"{self.registry_url}/v2/{repo_path}/tags/list")
                    if t_resp.status_code == 200:
                        tags = t_resp.json().get("tags") or []
            except Exception:
                pass

            # Fetch MinIO disk usage
            size_human = "Unknown"
            object_count = 0
            exit_code, du_out = await asyncio.to_thread(
                self._exec_in_minio,
                f"mc du myminio/{self.registry_bucket}/docker/registry/v2/repositories/{repo_path}",
            )
            if exit_code == 0 and du_out.strip():
                # Format: 1.2KiB  18 objects  pantheon-registry/...
                du_parts = du_out.strip().split()
                if len(du_parts) >= 3:
                    size_human = du_parts[0]
                    try:
                        object_count = int(du_parts[1])
                    except ValueError:
                        pass

            # Check if linked to an active DB application
            is_active = False
            if active_app_names is not None:
                # Match clean name or repo_name
                is_active = (
                    clean_app_name.lower() in active_app_names
                    or repo_name.lower() in active_app_names
                )

            results.append({
                "repository": repo_path,
                "name": repo_name,
                "clean_app_name": clean_app_name,
                "org_id": org_id,
                "tags": tags,
                "size_human": size_human,
                "object_count": object_count,
                "is_orphaned": not is_active,
                "bucket": self.registry_bucket,
                "minio_path": f"{self.registry_bucket}/docker/registry/v2/repositories/{repo_path}",
            })

        return results

    async def delete_repository(
        self, repository_path: str, purge_local_docker: bool = True
    ) -> dict[str, Any]:
        """Delete an image repository from MinIO, run garbage collection, and purge local Docker images."""
        clean_path = repository_path.strip().strip("/")
        repo_name = clean_path.split("/")[-1]
        service_name = sanitize_docker_name(repo_name.removeprefix("app-"))

        logger.info("purging_repository_from_minio", repository=clean_path)

        # 1. Remove repository directory from MinIO pantheon-registry bucket
        minio_target = f"myminio/{self.registry_bucket}/docker/registry/v2/repositories/{clean_path}"
        code, out = await asyncio.to_thread(
            self._exec_in_minio, f"mc rm --recursive --force {minio_target}"
        )
        minio_success = (code == 0)

        # 2. Trigger Docker Registry garbage collection inside registry container to reclaim blobs
        gc_code, gc_out = await asyncio.to_thread(
            self._exec_in_registry,
            ["bin/registry", "garbage-collect", "-m", "/etc/docker/registry/config.yml"],
        )

        # 3. Purge matching artifacts in pantheon-artifacts bucket if any exist
        artifact_target = f"myminio/{self.artifacts_bucket}/{clean_path}"
        await asyncio.to_thread(
            self._exec_in_minio, f"mc rm --recursive --force {artifact_target}"
        )

        # 4. Optional: Clean up local Docker daemon cache (images & stopped preview containers)
        docker_cleanup_info: dict[str, Any] = {"images_removed": [], "containers_removed": []}
        if purge_local_docker:
            client = self._get_docker_client()
            if client:
                # Stop & remove container pantheon-app-{service_name} or pantheon-app-{repo_name}
                candidate_containers = [
                    f"pantheon-app-{service_name}",
                    f"pantheon-app-{repo_name.lower()}",
                ]
                for cname in candidate_containers:
                    try:
                        c = client.containers.get(cname)
                        try:
                            c.stop(timeout=2)
                        except Exception:
                            pass
                        c.remove(force=True)
                        docker_cleanup_info["containers_removed"].append(cname)
                    except Exception:
                        pass

                # Remove local Docker images matching repository path or service name
                try:
                    for img in client.images.list():
                        tags = img.tags or []
                        should_remove = False
                        for t in tags:
                            if clean_path in t or f":5000/{clean_path}" in t or f"pantheon-app-{service_name}" in t:
                                should_remove = True
                                break
                        if should_remove:
                            try:
                                client.images.remove(img.id, force=True)
                                docker_cleanup_info["images_removed"].append(img.short_id)
                            except Exception as rm_err:
                                logger.debug("docker_image_rm_failed", id=img.short_id, error=str(rm_err))
                except Exception as img_err:
                    logger.warning("docker_image_list_failed", error=str(img_err))

        return {
            "status": "purged",
            "repository": clean_path,
            "minio_purged": minio_success,
            "registry_gc_success": (gc_code == 0),
            "docker_cleanup": docker_cleanup_info,
            "output": out,
        }

    async def delete_app_storage(
        self, app_name: str, org_id: str | None = None, purge_local_docker: bool = True
    ) -> dict[str, Any]:
        """Find and purge all MinIO and Registry storage associated with an application name."""
        all_repos = await self.list_repositories()
        clean_name = sanitize_docker_name(app_name)

        deleted_repos: list[str] = []
        for r in all_repos:
            repo_path = r["repository"]
            name = r["name"].lower()
            # Match app-xyz, xyz, or exact match
            if name == f"app-{clean_name}" or name == clean_name or r["clean_app_name"].lower() == clean_name:
                if not org_id or org_id in repo_path:
                    await self.delete_repository(repo_path, purge_local_docker=purge_local_docker)
                    deleted_repos.append(repo_path)

        return {
            "app_name": app_name,
            "deleted_repositories": deleted_repos,
        }


minio_service = MinioStorageService()
