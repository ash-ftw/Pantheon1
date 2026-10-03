"""AI Dockerfile Generator Agent — Powered by Groq.

Autonomously inspects repository manifests (package.json, bun.lock, requirements.txt, etc.),
analyzes project structure and scripts, and prompts Groq (LLaMA/GPT-OSS) to synthesize
an optimized, multi-stage, production-ready Dockerfile strictly tailored to Pantheon's
runtime invariants (HOST=0.0.0.0, PORT=8085, CLIENT_ORIGIN).
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

# Fallback models available on Groq if primary model is unavailable
GROQ_MODEL_FALLBACKS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "groq/compound",
    "llama-3.3-70b-versatile",
]

SYSTEM_PROMPT = """You are Pantheon's Senior DevSecOps & Containerization AI Agent.
Your job is to generate an optimized, secure, production-grade Dockerfile tailored to the user's application repository.

CRITICAL PANTHEON RUNTIME INVARIANTS:
1. Base Image: Use lean official images (e.g. `node:20-alpine`, `oven/bun:alpine`, `python:3.12-slim`, `golang:1.22-alpine`).
2. Workdir: Always set `WORKDIR /app`.
3. Platform Environment Variables:
   Must include:
   ENV PORT=8085
   ENV HOST=0.0.0.0
   ENV CLIENT_ORIGIN=http://localhost:5173
   ENV CI=true
   ENV FORCE_COLOR=0
4. Port Exposure: Always `EXPOSE 8085` (or project's main port).
5. Package Managers & Base Images:
   - ALWAYS use glibc-based images (`oven/bun:debian`, `node:20-bookworm-slim`, `python:3.11-slim`) instead of Alpine. Modern frontend and fullstack packages (e.g. Cloudflare workerd, TanStack Start, esbuild, Prisma, Sharp) require glibc native binaries and fail with AssertionError or ENOENT on musl Alpine.
   - If Bun (bun.lock / bunfig.toml), use `oven/bun:debian`; run `bun install`.
   - If pnpm (pnpm-lock.yaml), use `node:20-bookworm-slim`, install pnpm (`npm install -g pnpm`) and run `pnpm install`.
   - If Yarn (yarn.lock), use `node:20-bookworm-slim`, run `yarn install`.
   - If npm, use `node:20-bookworm-slim`, always use `npm install --legacy-peer-deps --no-audit --no-fund` to prevent peer dependency conflict hangs.
6. Build & Serving Strategy:
   - Check dependencies for fullstack SSR frameworks: `@tanstack/react-start`, `@tanstack/react-router`, `next`, `@remix-run/`, `nuxt`, `astro`, `@sveltejs/kit`.
   - If an SSR / fullstack framework is detected:
     DO NOT use static `serve -s dist` (because dist has no static index.html; pages are rendered dynamically).
     Run `RUN bun run build` (or `RUN npm run build`) during the Docker build stage.
     For runtime CMD:
     - If package.json has a "preview" script: `CMD ["sh", "-c", "bun run preview --host 0.0.0.0 --port ${PORT:-8085}"]` or `CMD ["sh", "-c", "npm run preview -- --host 0.0.0.0 --port ${PORT:-8085}"]`.
     - If Next.js: `CMD ["sh", "-c", "npm start -- -p ${PORT:-8085} -H 0.0.0.0"]`.
     - If package.json has "start": `CMD ["sh", "-c", "npm start"]` or `CMD ["sh", "-c", "bun run start"]`.
     - Otherwise: `CMD ["sh", "-c", "bun run dev --host 0.0.0.0 --port ${PORT:-8085}"]`.
   - For pure static SPA apps (classic React/Vite with index.html in root, Vue, HTML):
     Run `RUN bun run build` or `RUN npm run build`, and serve:
     `CMD ["sh", "-c", "serve -s dist -l ${PORT:-8085}"]`.
     CRITICAL: In `serve`, the `-l` parameter MUST ONLY be the port number (e.g. `-l 8085` or `-l ${PORT:-8085}`). NEVER pass `-l ${HOST}:${PORT}` or `-l 0.0.0.0:8085`.
7. Entrypoint / Command:
   - Use `CMD ["/bin/sh", "-c", "..."]` or direct `CMD [...]`.
   - Must run non-interactively and bind to 0.0.0.0:${PORT:-8085}.
8. Formatting: Output ONLY valid Dockerfile instructions. DO NOT wrap with markdown fences (no ```dockerfile). NO chit-chat.
"""


class AIDockerfileGenerator:
    """Agent that inspects a repository and generates a validated Dockerfile via Groq."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = settings.groq_api_key if api_key is None else api_key
        self.base_url = (settings.groq_base_url if base_url is None else base_url).rstrip("/")
        self.model = settings.groq_model if model is None else model

    @property
    def is_configured(self) -> bool:
        """Check if Groq API key is present."""
        return bool(self.api_key and self.api_key.strip() and not self.api_key.startswith("gsk-your-"))

    def inspect_repository(self, scratch_dir: str | Path) -> dict[str, Any]:
        """Scan cloned repository files and manifests to assemble context for the LLM."""
        repo_path = Path(scratch_dir)
        context: dict[str, Any] = {
            "root_files": [],
            "directories": [],
            "package_manager": "npm",
            "manifests": {},
            "scripts": {},
            "dependencies": [],
            "entrypoint_candidates": [],
        }

        if not repo_path.exists():
            return context

        try:
            # 1. Top-level files and directories
            for item in repo_path.iterdir():
                if item.name.startswith(".") and item.name not in (".env.example", ".env.local"):
                    continue
                if item.is_dir() and item.name not in ("node_modules", ".git", "venv", ".venv", "__pycache__"):
                    context["directories"].append(item.name)
                elif item.is_file():
                    context["root_files"].append(item.name)

            # 2. Detect package managers & lockfiles
            if (repo_path / "bun.lock").exists() or (repo_path / "bun.lockb").exists() or (repo_path / "bunfig.toml").exists():
                context["package_manager"] = "bun"
            elif (repo_path / "pnpm-lock.yaml").exists():
                context["package_manager"] = "pnpm"
            elif (repo_path / "yarn.lock").exists():
                context["package_manager"] = "yarn"
            elif (repo_path / "package-lock.json").exists():
                context["package_manager"] = "npm"

            # 3. Read package.json if present
            pkg_json_path = repo_path / "package.json"
            if pkg_json_path.exists():
                try:
                    pkg_data = json.loads(pkg_json_path.read_text(encoding="utf-8", errors="ignore"))
                    context["manifests"]["package.json"] = {
                        "name": pkg_data.get("name"),
                        "type": pkg_data.get("type"),
                        "scripts": pkg_data.get("scripts", {}),
                        "dependencies": list(pkg_data.get("dependencies", {}).keys()),
                        "devDependencies": list(pkg_data.get("devDependencies", {}).keys()),
                        "workspaces": pkg_data.get("workspaces"),
                    }
                    context["scripts"] = pkg_data.get("scripts", {})
                    context["dependencies"] = list(pkg_data.get("dependencies", {}).keys())
                except Exception as e:
                    logger.debug("failed_reading_package_json", error=str(e))

            # 4. Python manifests
            req_path = repo_path / "requirements.txt"
            if req_path.exists():
                try:
                    req_content = req_path.read_text(encoding="utf-8", errors="ignore").splitlines()[:30]
                    context["manifests"]["requirements.txt"] = [
                        line.strip() for line in req_content if line.strip() and not line.strip().startswith("#")
                    ]
                except Exception:
                    pass

            pyproject_path = repo_path / "pyproject.toml"
            if pyproject_path.exists():
                context["manifests"]["pyproject.toml"] = pyproject_path.read_text(encoding="utf-8", errors="ignore")[:500]

            # 5. Look for key entrypoints
            for pattern in ("index.ts", "index.js", "server.ts", "server.js", "main.ts", "main.js", "app.py", "main.py"):
                matches = list(repo_path.glob(f"**/{pattern}"))
                filtered = [
                    str(m.relative_to(repo_path))
                    for m in matches
                    if "node_modules" not in str(m) and ".git" not in str(m)
                ][:3]
                context["entrypoint_candidates"].extend(filtered)

        except Exception as e:
            logger.warning("repository_inspection_partial_failure", error=str(e))

        return context

    def _build_user_prompt(self, repo_context: dict[str, Any], detection: dict[str, Any]) -> str:
        """Construct detailed prompt describing project layout and requirements."""
        pkg_manager = repo_context.get("package_manager", "npm")
        scripts = repo_context.get("scripts", {})
        deps = repo_context.get("dependencies", [])
        entrypoints = repo_context.get("entrypoint_candidates", [])
        detected_lang = detection.get("primary_language", "Unknown")
        detected_framework = detection.get("framework", "Unknown")

        manifests_summary = json.dumps(repo_context.get("manifests", {}), indent=2)

        return f"""Analyze this project and generate an optimal, multi-stage Dockerfile for Pantheon:

DETECTED STACK:
- Language: {detected_lang}
- Framework: {detected_framework}
- Preferred Package Manager: {pkg_manager}

PROJECT DETAILS:
- Root Files: {', '.join(repo_context.get('root_files', [])[:20])}
- Root Directories: {', '.join(repo_context.get('directories', [])[:10])}
- NPM Scripts: {json.dumps(scripts)}
- Top Dependencies ({len(deps)} total): {', '.join(deps[:15])}
- Entrypoint Candidates: {', '.join(entrypoints[:5])}

PROJECT MANIFESTS (truncated):
{manifests_summary[:2000]}

Generate a complete, ready-to-run Dockerfile adhering strictly to the system prompt instructions.
"""

    def validate_dockerfile(self, content: str) -> tuple[bool, str, str]:
        """Validate synthesized Dockerfile syntax, platform invariants, and strip markdown fences.

        Returns (is_valid, cleaned_content, reason).
        """
        if not content or not content.strip():
            return False, "", "Empty content received from LLM."

        # Strip markdown code fences if model enclosed response in ```dockerfile ... ```
        cleaned = re.sub(r"^```(?:dockerfile|docker)?\s*", "", content.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())
        cleaned = cleaned.strip()

        lines = [line.strip() for line in cleaned.splitlines() if line.strip() and not line.strip().startswith("#")]
        if not lines:
            return False, "", "No active Dockerfile instructions found."

        # Check for FROM instruction
        has_from = any(line.upper().startswith("FROM ") for line in lines)
        if not has_from:
            return False, "", "Missing FROM instruction."

        # Check for WORKDIR instruction
        has_workdir = any(line.upper().startswith("WORKDIR ") for line in lines)
        if not has_workdir:
            return False, "", "Missing WORKDIR instruction."

        # Check for CMD or ENTRYPOINT
        has_cmd = any(line.upper().startswith("CMD ") or line.upper().startswith("ENTRYPOINT ") for line in lines)
        if not has_cmd:
            return False, "", "Missing CMD or ENTRYPOINT instruction."

        # Ensure PORT and HOST are defined or defaulted
        has_port_env = any("PORT" in line.upper() for line in lines)
        has_expose = any(line.upper().startswith("EXPOSE ") for line in lines)
        if not has_port_env and not has_expose:
            # Automatically inject standard port bindings if omitted
            cleaned += "\nENV PORT=8085\nENV HOST=0.0.0.0\nEXPOSE 8085\n"

        # Ensure CLIENT_ORIGIN is present
        if "CLIENT_ORIGIN" not in cleaned:
            cleaned = "ENV CLIENT_ORIGIN=http://localhost:5173\n" + cleaned

        # Ensure CI=true is present to prevent interactive prompt hangs
        if "ENV CI=" not in cleaned:
            cleaned = "ENV CI=true\nENV FORCE_COLOR=0\n" + cleaned

        # Sanitize any serve command with invalid host:port format (serve expects only port)
        # e.g., "serve -s dist -l ${HOST}:${PORT}" -> "serve -s dist -l ${PORT:-8085}"
        cleaned = re.sub(
            r"(serve\s+[^\"\n\r]+)-l\s+(?:\$\{?HOST\}?:|0\.0\.0\.0:)(?:\$\{?PORT(?::-8085)?\}?|\d+)",
            r"\1-l ${PORT:-8085}",
            cleaned,
        )

        return True, cleaned, "Valid Dockerfile."

    async def generate_dockerfile(
        self,
        scratch_dir: str | Path,
        detection: dict[str, Any],
        log_callback: Callable[[str], None] | None = None,
    ) -> Path | None:
        """Execute agentic Dockerfile generation.

        Returns Path to the generated Dockerfile if successful and validated,
        or None if generation fails (signaling fallback to heuristic presets).
        """
        def _log(msg: str) -> None:
            if log_callback:
                log_callback(msg)

        if not self.is_configured:
            _log("[AI Agent] Groq API key not configured. Proceeding with deterministic heuristic generator.")
            return None

        dockerfile_path = Path(scratch_dir) / "Dockerfile"

        # 1. Inspect repository
        _log("[AI Agent] Inspecting repository manifests, lockfiles, and directory structure...")
        repo_context = self.inspect_repository(scratch_dir)
        pkg_manager = repo_context.get("package_manager", "npm")
        framework = detection.get("framework", "Unknown")
        primary_lang = detection.get("primary_language", "Unknown")

        _log(f"[AI Agent] Repository analysis: {primary_lang} / {framework} (Package Manager: {pkg_manager})")

        # 2. Build prompt
        user_prompt = self._build_user_prompt(repo_context, detection)

        # 3. Query Groq with model fallback
        models_to_try = [self.model] + [m for m in GROQ_MODEL_FALLBACKS if m != self.model]

        raw_dockerfile: str | None = None
        used_model: str = self.model

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=settings.groq_timeout) as client:
            for model_name in models_to_try:
                _log(f"[AI Agent] Synthesizing optimized multi-stage Dockerfile via Groq ({model_name})...")
                start_time = time.time()
                try:
                    payload = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": settings.groq_temperature,
                    }

                    url = f"{self.base_url}/chat/completions"
                    resp = await client.post(url, headers=headers, json=payload)

                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            raw_dockerfile = choices[0].get("message", {}).get("content", "")
                            elapsed = round(time.time() - start_time, 2)
                            used_model = model_name
                            _log(f"[AI Agent] Received Dockerfile synthesis from {model_name} in {elapsed}s.")
                            break
                    else:
                        logger.warning(
                            "groq_model_call_failed",
                            model=model_name,
                            status=resp.status_code,
                            body=resp.text[:200],
                        )
                except Exception as e:
                    logger.warning("groq_api_call_exception", model=model_name, error=str(e))
                    continue

        if not raw_dockerfile:
            _log("[AI Agent] Groq service did not return a response. Falling back to heuristic generator.")
            return None

        # 4. Validate synthesized Dockerfile
        _log("[AI Agent] Validating generated Dockerfile syntax and Pantheon runtime invariants...")
        is_valid, cleaned_dockerfile, reason = self.validate_dockerfile(raw_dockerfile)

        if not is_valid:
            _log(f"[AI Agent] Validation failed ({reason}). Falling back to heuristic generator.")
            return None

        # 5. Write validated Dockerfile
        try:
            dockerfile_path.write_text(cleaned_dockerfile, encoding="utf-8")
            _log(f"[AI Agent] Dockerfile verified and saved successfully (Generated via Groq / {used_model}).")
            logger.info("ai_dockerfile_generated_successfully", model=used_model, path=str(dockerfile_path))
            return dockerfile_path
        except Exception as e:
            _log(f"[AI Agent] Failed to save Dockerfile: {e!s}. Falling back to heuristic generator.")
            return None


# Global singleton instance
ai_dockerfile_generator = AIDockerfileGenerator()
