"""Docker Image Builder & Registry Push — PRD Module 4 Items 3, 6.

Uses docker-py to build images via Docker BuildKit and push to the
MinIO-backed registry:2 instance. Supports streaming build logs for
real-time WebSocket forwarding.
"""

import subprocess
from pathlib import Path
from typing import Any

import docker
from docker.errors import BuildError, DockerException

from app.config import settings
from app.logging import get_logger

logger = get_logger(__name__)


class DockerBuildError(Exception):
    """Raised when a Docker build or push operation fails."""


class DockerBuilder:
    """Builds container images and pushes them to the local registry.

    Architecture:
        Source directory → docker build (BuildKit) → tag → push → registry:2 → MinIO S3

    The registry:2 service stores all image layers in MinIO's
    'pantheon-registry' bucket via the S3 storage driver.
    """

    def __init__(self) -> None:
        self._client: docker.DockerClient | None = None
        self._initialized = False
        self._available = False

    def _get_client(self) -> docker.DockerClient | None:
        """Lazy-init Docker client. Returns None if Docker daemon is unreachable."""
        if self._initialized:
            return self._client

        self._initialized = True
        try:
            self._client = docker.from_env()
            self._client.ping()
            self._available = True
            logger.info("docker_client_connected", version=self._client.version().get("Version"))
        except DockerException as e:
            logger.warning("docker_daemon_unavailable", error=str(e))
            self._client = None
            self._available = False

        return self._client

    @property
    def is_available(self) -> bool:
        """Check if Docker daemon is reachable."""
        self._get_client()
        return self._available

    def build_image(
        self,
        build_context: str,
        image_tag: str,
        dockerfile: str = "Dockerfile",
        log_callback: Any = None,
    ) -> dict[str, Any]:
        """Build a Docker image from a source directory.

        Args:
            build_context: Path to the directory containing the Dockerfile and source.
            image_tag: Full image tag including registry, e.g. localhost:5000/org-xxx/app-foo:v1.
            dockerfile: Relative path to Dockerfile within build_context.
            log_callback: Optional callable(str) for streaming build log lines.

        Returns:
            {"image_id": str, "tag": str, "size_mb": float, "logs": list[str]}

        Raises:
            DockerBuildError: If Docker daemon is unavailable or build fails.
        """
        client = self._get_client()
        if not client:
            raise DockerBuildError(
                "Docker daemon is not running. Start Docker Desktop or Docker Engine."
            )

        build_path = Path(build_context)
        dockerfile_path = build_path / dockerfile
        if not dockerfile_path.exists():
            raise DockerBuildError(
                f"Dockerfile not found at {dockerfile_path}. "
                "Ensure the repository contains a Dockerfile."
            )

        build_logs: list[str] = []

        def _log(msg: str) -> None:
            build_logs.append(msg)
            if log_callback:
                log_callback(msg)

        _log(f"Building image: {image_tag}")
        _log(f"Build context: {build_context}")
        _log(f"Dockerfile: {dockerfile}")

        try:
            # Build with BuildKit (DOCKER_BUILDKIT=1) and stream logs
            image, log_stream = client.images.build(
                path=build_context,
                dockerfile=dockerfile,
                tag=image_tag,
                rm=True,           # Remove intermediate containers
                forcerm=True,      # Force removal on error
                buildargs={"BUILDKIT_INLINE_CACHE": "1"},
            )

            # Stream build log lines
            for chunk in log_stream:
                if "stream" in chunk:
                    line = chunk["stream"].strip()
                    if line:
                        _log(line)
                elif "error" in chunk:
                    error_msg = chunk["error"].strip()
                    _log(f"BUILD ERROR: {error_msg}")
                    raise DockerBuildError(f"Docker build failed: {error_msg}")

            # Get image size
            image.reload()
            size_bytes = image.attrs.get("Size", 0)
            size_mb = round(size_bytes / (1024 * 1024), 2)

            _log(f"Image built successfully: {image.short_id} ({size_mb} MB)")

            return {
                "image_id": image.id,
                "tag": image_tag,
                "size_mb": size_mb,
                "logs": build_logs,
            }

        except BuildError as e:
            error_msg = f"Docker build failed: {e!s}"
            _log(error_msg)
            # Include the last few build log lines for context
            for log_entry in (e.build_log or [])[-5:]:
                if isinstance(log_entry, dict) and "stream" in log_entry:
                    _log(f"  > {log_entry['stream'].strip()}")
            raise DockerBuildError(error_msg) from e

    def push_image(
        self,
        image_tag: str,
        log_callback: Any = None,
    ) -> dict[str, Any]:
        """Push a built image to the MinIO-backed registry.

        Args:
            image_tag: Full image tag, e.g. localhost:5000/org-xxx/app-foo:v1.
            log_callback: Optional callable(str) for streaming push log lines.

        Returns:
            {"tag": str, "digest": str | None, "logs": list[str]}

        Raises:
            DockerBuildError: If push fails.
        """
        client = self._get_client()
        if not client:
            raise DockerBuildError("Docker daemon is not running.")

        push_logs: list[str] = []

        def _log(msg: str) -> None:
            push_logs.append(msg)
            if log_callback:
                log_callback(msg)

        _log(f"Pushing image to registry: {image_tag}")

        try:
            # Push and stream progress
            push_output = client.images.push(
                image_tag,
                stream=True,
                decode=True,
            )

            digest = None
            for chunk in push_output:
                if "status" in chunk:
                    status = chunk["status"]
                    progress = chunk.get("progress", "")
                    if progress:
                        _log(f"  {status}: {progress}")
                    elif "Digest" in status or "digest" in status:
                        _log(f"  {status}")
                    elif "error" not in chunk:
                        _log(f"  {status}")

                if "error" in chunk:
                    error_msg = chunk["error"].strip()
                    _log(f"PUSH ERROR: {error_msg}")
                    raise DockerBuildError(f"Registry push failed: {error_msg}")

                # Capture the digest from the push response
                if "aux" in chunk and "Digest" in chunk["aux"]:
                    digest = chunk["aux"]["Digest"]

            _log(f"Image pushed successfully: {image_tag}")
            if digest:
                _log(f"Digest: {digest}")

            return {
                "tag": image_tag,
                "digest": digest,
                "logs": push_logs,
            }

        except DockerException as e:
            error_msg = f"Registry push failed: {e!s}"
            _log(error_msg)
            raise DockerBuildError(error_msg) from e

    def build_with_buildpacks(
        self,
        source_dir: str,
        image_tag: str,
        log_callback: Any = None,
    ) -> dict[str, Any]:
        """Build an image using Paketo Buildpacks when no Dockerfile is present.

        Falls back to `pack` CLI 0.35+ with builder-jammy-base.

        Args:
            source_dir: Path to source code directory.
            image_tag: Target image tag.
            log_callback: Optional callable(str) for log streaming.

        Returns:
            {"image_id": str | None, "tag": str, "logs": list[str]}

        Raises:
            DockerBuildError: If pack CLI is not installed or build fails.
        """
        build_logs: list[str] = []

        def _log(msg: str) -> None:
            build_logs.append(msg)
            if log_callback:
                log_callback(msg)

        _log("No Dockerfile found. Building with Paketo Buildpacks (pack CLI)...")
        _log(f"Source: {source_dir}")
        _log(f"Target: {image_tag}")
        _log("Builder: paketobuildpacks/builder-jammy-base")

        try:
            result = subprocess.run(  # noqa: S603
                [
                    "pack", "build", image_tag,
                    "--path", source_dir,
                    "--builder", "paketobuildpacks/builder-jammy-base",
                    "--trust-builder",
                ],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            # Stream stdout lines
            for line in result.stdout.splitlines():
                _log(line)

            if result.returncode != 0:
                for line in result.stderr.splitlines():
                    _log(f"ERROR: {line}")
                raise DockerBuildError(
                    f"Buildpack build failed (exit code {result.returncode}): "
                    f"{result.stderr[:500]}"
                )

            _log("Buildpack build completed successfully.")
            return {
                "image_id": None,  # pack CLI doesn't return image ID directly
                "tag": image_tag,
                "logs": build_logs,
            }

        except FileNotFoundError:
            _log("WARNING: 'pack' CLI not found. Install Paketo Buildpacks CLI:")
            _log("  https://buildpacks.io/docs/for-platform-operators/how-to/integrate-ci/pack/")
            raise DockerBuildError(
                "'pack' CLI is not installed. Cannot build without Dockerfile or Buildpacks."
            )

        except subprocess.TimeoutExpired:
            raise DockerBuildError("Buildpack build timed out after 10 minutes.")


# Global singleton
docker_builder = DockerBuilder()
