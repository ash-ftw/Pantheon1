"""Unit tests for AI Dockerfile Generator Agent (Groq / LLaMA / GPT-OSS)."""

import json
import tempfile
from pathlib import Path

import pytest

from app.services.ai_dockerfile_generator import AIDockerfileGenerator, ai_dockerfile_generator


def test_inspect_repository_detects_bun_and_scripts() -> None:
    """Verify inspection detects Bun lockfile, manifests, and scripts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "bun.lock").write_text("lock content", encoding="utf-8")
        pkg = {
            "name": "test-app",
            "scripts": {"build": "vite build", "start": "vite preview"},
            "dependencies": {"react": "^19.0.0", "vite": "^5.0.0"},
        }
        (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
        (root / "src").mkdir()
        (root / "src" / "main.tsx").write_text("console.log('hi')", encoding="utf-8")

        agent = AIDockerfileGenerator()
        context = agent.inspect_repository(tmpdir)

        assert context["package_manager"] == "bun"
        assert "package.json" in context["manifests"]
        assert context["scripts"]["build"] == "vite build"
        assert "react" in context["dependencies"]


def test_validate_dockerfile_clean_and_strips_markdown_fences() -> None:
    """Verify validation strips markdown fences and validates required instructions."""
    raw = """```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm run build
EXPOSE 8085
CMD ["npm", "start"]
```"""
    agent = AIDockerfileGenerator()
    is_valid, cleaned, _reason = agent.validate_dockerfile(raw)

    assert is_valid is True
    assert "```" not in cleaned
    assert "FROM node:20-alpine" in cleaned
    assert "WORKDIR /app" in cleaned
    assert "EXPOSE 8085" in cleaned
    assert "CLIENT_ORIGIN=http://localhost:5173" in cleaned


def test_validate_dockerfile_missing_from_rejected() -> None:
    """Verify validation rejects content missing FROM."""
    raw = 'WORKDIR /app\nRUN npm install\nCMD ["npm", "start"]'
    agent = AIDockerfileGenerator()
    is_valid, _, reason = agent.validate_dockerfile(raw)

    assert is_valid is False
    assert "Missing FROM" in reason


def test_validate_dockerfile_missing_cmd_rejected() -> None:
    """Verify validation rejects content missing CMD or ENTRYPOINT."""
    raw = "FROM node:20-alpine\nWORKDIR /app\nEXPOSE 8085\nRUN npm install"
    agent = AIDockerfileGenerator()
    is_valid, _, reason = agent.validate_dockerfile(raw)

    assert is_valid is False
    assert "Missing CMD" in reason


@pytest.mark.asyncio
async def test_generate_dockerfile_returns_none_when_unconfigured() -> None:
    """Verify agent gracefully returns None when API key is unconfigured."""
    agent = AIDockerfileGenerator(api_key="")
    logs: list[str] = []
    res = await agent.generate_dockerfile(
        tempfile.gettempdir(), {"framework": "Vite"}, log_callback=logs.append
    )

    assert res is None
    assert any("not configured" in line for line in logs)


@pytest.mark.asyncio
async def test_generate_dockerfile_live_with_configured_groq() -> None:
    """Verify live generation produces a valid, runnable Dockerfile with Groq."""
    if not ai_dockerfile_generator.is_configured:
        pytest.skip("Groq API key not configured")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "bun.lock").write_text("lockfile", encoding="utf-8")
        pkg = {
            "name": "sample-project",
            "scripts": {"build": "vite build"},
            "dependencies": {"react": "^19.0.0"},
        }
        (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")

        logs: list[str] = []
        df_path = await ai_dockerfile_generator.generate_dockerfile(
            scratch_dir=tmpdir,
            detection={"framework": "Vite", "primary_language": "TypeScript (React)"},
            log_callback=logs.append,
        )

        assert df_path is not None
        assert df_path.exists()
        content = df_path.read_text(encoding="utf-8")
        assert "FROM " in content
        assert "WORKDIR " in content
        assert "EXPOSE 8085" in content
        assert any("[AI Agent]" in log for log in logs)
