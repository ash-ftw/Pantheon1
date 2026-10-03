"""Unit tests for DockerBuilder error resilience and multi-stack framework detection."""

import itertools
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from docker.errors import BuildError

from app.services.docker_builder import DockerBuildError, docker_builder
from app.services.language_detector import language_detector
from app.tasks.ingestion import _generate_dockerfile


def test_docker_builder_handles_itertools_tee_build_log() -> None:
    """Verify docker_builder handles itertools._tee build_log without TypeError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dockerfile = Path(tmpdir) / "Dockerfile"
        dockerfile.write_text("FROM alpine:latest\nRUN exit 1\n")

        # Simulate docker-py's itertools._tee iterator for BuildError
        mock_log_stream = itertools.tee(
            [
                {"stream": "Step 1/2 : FROM alpine:latest\n"},
                {"stream": "Step 2/2 : RUN exit 1\n"},
                {"error": "The command '/bin/sh -c exit 1' returned a non-zero code: 1\n"},
            ]
        )[0]

        mock_client = MagicMock()
        mock_client.images.build.side_effect = BuildError(
            reason="The command '/bin/sh -c exit 1' returned a non-zero code: 1",
            build_log=mock_log_stream,
        )

        with patch.object(docker_builder, "_get_client", return_value=mock_client):
            captured_logs: list[str] = []
            with pytest.raises(DockerBuildError) as exc_info:
                docker_builder.build_image(
                    build_context=tmpdir,
                    image_tag="test:v1",
                    dockerfile="Dockerfile",
                    log_callback=captured_logs.append,
                )

            assert "Docker build failed" in str(exc_info.value)
            # Verify build log was safely consumed
            assert any("RUN exit 1" in line for line in captured_logs)


def test_language_detector_fastify_stack() -> None:
    """Verify Fastify is detected from package.json dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "package.json"
        pkg_path.write_text(
            json.dumps(
                {
                    "name": "fastify-api",
                    "dependencies": {"fastify": "^4.26.0"},
                    "scripts": {"start": "node server.js"},
                }
            )
        )
        (Path(tmpdir) / "server.js").write_text("const fastify = require('fastify')();")

        result = language_detector.detect(tmpdir)
        assert result["framework"] == "Fastify"
        assert result["framework_category"] == "node_backend"
        assert result["primary_language"] == "JavaScript"
        assert language_detector.get_display_string(result) == "JavaScript / Fastify"


def test_language_detector_express_and_nestjs() -> None:
    """Verify Express and NestJS detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "package.json"
        pkg_path.write_text(
            json.dumps(
                {
                    "name": "express-api",
                    "dependencies": {"express": "^4.19.0"},
                }
            )
        )
        (Path(tmpdir) / "app.js").write_text("const express = require('express');")

        result = language_detector.detect(tmpdir)
        assert result["framework"] == "Express.js"
        assert result["framework_category"] == "node_backend"

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "package.json"
        pkg_path.write_text(
            json.dumps(
                {
                    "name": "nest-api",
                    "dependencies": {"@nestjs/core": "^10.0.0"},
                }
            )
        )
        result = language_detector.detect(tmpdir)
        assert result["framework"] == "NestJS"
        assert result["framework_category"] == "node_backend"


def test_generate_dockerfile_fastify_backend() -> None:
    """Verify Fastify generates backend-friendly Dockerfile with HOST=0.0.0.0 and no vite build."""
    with tempfile.TemporaryDirectory() as tmpdir:
        detection = {
            "primary_language": "JavaScript",
            "framework": "Fastify",
            "framework_category": "node_backend",
        }
        df_path = _generate_dockerfile(detection, tmpdir)
        assert df_path.exists()
        content = df_path.read_text()

        # Must not contain npx vite build
        assert "npx vite build" not in content
        # Must bind to 0.0.0.0 for container networking
        assert "HOST=0.0.0.0" in content
        assert "PORT=8085" in content
        assert "EXPOSE 8085" in content
        # Must execute server entry point
        assert "node server.js" in content


def test_generate_dockerfile_frontend_resilience() -> None:
    """Verify frontend Dockerfile generation uses resilient build fallback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        detection = {
            "primary_language": "TypeScript (React)",
            "framework": "Vite",
            "framework_category": "node_frontend",
        }
        df_path = _generate_dockerfile(detection, tmpdir)
        assert df_path.exists()
        content = df_path.read_text()

        # Must have fallback to avoid crashing on build errors
        assert "|| true" in content
        assert "npx serve" in content
        assert "PORT=8085" in content
