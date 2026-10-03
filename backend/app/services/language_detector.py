"""Language & Framework Detector — PRD Module 4 Item 10.

File-based language and framework detection using file extension heuristics,
direct package manifest inspection (package.json, pyproject.toml, go.mod),
and known framework marker files.
"""

import json
from pathlib import Path
from typing import Any, TypedDict

from app.logging import get_logger

logger = get_logger(__name__)


class FrameworkMarker(TypedDict):
    marker: str
    content_check: str | None
    framework: str


# Categorization mappings for Dockerfile generation & profiling
NODE_BACKEND_FRAMEWORKS = {
    "Fastify",
    "Express.js",
    "NestJS",
    "Koa",
    "Hapi",
    "Hono",
    "Elysia",
    "AdonisJS",
}

NODE_FRONTEND_FRAMEWORKS = {
    "React",
    "Vite",
    "Next.js",
    "Nuxt.js",
    "Vue.js",
    "Angular",
    "SvelteKit",
    "Astro",
    "Remix",
    "SolidJS",
}

PYTHON_FRAMEWORKS = {
    "FastAPI",
    "Django",
    "Flask",
    "Tornado",
    "Sanic",
    "Litestar",
    "Aiohttp",
}

GO_FRAMEWORKS = {
    "Gin",
    "Fiber",
    "Echo",
    "Chi",
    "Go Module",
}

JAVA_FRAMEWORKS = {
    "Spring Boot",
    "Quarkus",
    "Micronaut",
    "Maven",
    "Gradle",
    "Gradle (Kotlin)",
}

RUST_FRAMEWORKS = {
    "Actix Web",
    "Axum",
    "Rocket",
    "Cargo",
}

PHP_FRAMEWORKS = {
    "Laravel",
    "Symfony",
    "Composer",
}

RUBY_FRAMEWORKS = {
    "Ruby on Rails",
    "Sinatra",
    "Rack",
}

DOTNET_FRAMEWORKS = {
    "ASP.NET",
}


# File extension → language mapping (sorted by priority / commonality)
EXTENSION_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".jsx": "JavaScript (React)",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".swift": "Swift",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".scala": "Scala",
    ".clj": "Clojure",
    ".hs": "Haskell",
    ".dart": "Dart",
    ".r": "R",
    ".lua": "Lua",
}

# Framework marker files and their corresponding framework names
FRAMEWORK_MARKERS: list[FrameworkMarker] = [
    # Python
    {"marker": "requirements.txt", "content_check": "fastapi", "framework": "FastAPI"},
    {"marker": "requirements.txt", "content_check": "django", "framework": "Django"},
    {"marker": "requirements.txt", "content_check": "flask", "framework": "Flask"},
    {"marker": "requirements.txt", "content_check": "tornado", "framework": "Tornado"},
    {"marker": "requirements.txt", "content_check": "sanic", "framework": "Sanic"},
    {"marker": "requirements.txt", "content_check": "litestar", "framework": "Litestar"},
    {"marker": "requirements.txt", "content_check": "aiohttp", "framework": "Aiohttp"},
    {"marker": "pyproject.toml", "content_check": "fastapi", "framework": "FastAPI"},
    {"marker": "pyproject.toml", "content_check": "django", "framework": "Django"},
    {"marker": "pyproject.toml", "content_check": "flask", "framework": "Flask"},
    {"marker": "pyproject.toml", "content_check": "tornado", "framework": "Tornado"},
    {"marker": "pyproject.toml", "content_check": "sanic", "framework": "Sanic"},
    {"marker": "pyproject.toml", "content_check": "litestar", "framework": "Litestar"},
    {"marker": "pyproject.toml", "content_check": "aiohttp", "framework": "Aiohttp"},
    {"marker": "Pipfile", "content_check": "fastapi", "framework": "FastAPI"},
    {"marker": "Pipfile", "content_check": "django", "framework": "Django"},
    {"marker": "Pipfile", "content_check": "flask", "framework": "Flask"},
    {"marker": "manage.py", "content_check": None, "framework": "Django"},
    # JavaScript / TypeScript config files
    {"marker": "next.config.js", "content_check": None, "framework": "Next.js"},
    {"marker": "next.config.mjs", "content_check": None, "framework": "Next.js"},
    {"marker": "next.config.ts", "content_check": None, "framework": "Next.js"},
    {"marker": "nuxt.config.ts", "content_check": None, "framework": "Nuxt.js"},
    {"marker": "nuxt.config.js", "content_check": None, "framework": "Nuxt.js"},
    {"marker": "astro.config.mjs", "content_check": None, "framework": "Astro"},
    {"marker": "astro.config.ts", "content_check": None, "framework": "Astro"},
    {"marker": "svelte.config.js", "content_check": None, "framework": "SvelteKit"},
    {"marker": "svelte.config.ts", "content_check": None, "framework": "SvelteKit"},
    {"marker": "angular.json", "content_check": None, "framework": "Angular"},
    {"marker": "vite.config.ts", "content_check": None, "framework": "Vite"},
    {"marker": "vite.config.js", "content_check": None, "framework": "Vite"},
    {"marker": "vite.config.mjs", "content_check": None, "framework": "Vite"},
    {"marker": "nest-cli.json", "content_check": None, "framework": "NestJS"},
    {"marker": "adonisrc.json", "content_check": None, "framework": "AdonisJS"},
    # Node package.json content checks (fallback if json parse doesn't match)
    {"marker": "package.json", "content_check": "fastify", "framework": "Fastify"},
    {"marker": "package.json", "content_check": "@nestjs/core", "framework": "NestJS"},
    {"marker": "package.json", "content_check": "express", "framework": "Express.js"},
    {"marker": "package.json", "content_check": "koa", "framework": "Koa"},
    {"marker": "package.json", "content_check": "@hapi/hapi", "framework": "Hapi"},
    {"marker": "package.json", "content_check": "hono", "framework": "Hono"},
    {"marker": "package.json", "content_check": "elysia", "framework": "Elysia"},
    {"marker": "package.json", "content_check": "@adonisjs", "framework": "AdonisJS"},
    {"marker": "package.json", "content_check": "@remix-run", "framework": "Remix"},
    {"marker": "package.json", "content_check": "astro", "framework": "Astro"},
    {"marker": "package.json", "content_check": "solid-js", "framework": "SolidJS"},
    {"marker": "package.json", "content_check": "react", "framework": "React"},
    {"marker": "package.json", "content_check": "vue", "framework": "Vue.js"},
    # Java / JVM
    {"marker": "pom.xml", "content_check": "spring-boot", "framework": "Spring Boot"},
    {"marker": "pom.xml", "content_check": "quarkus", "framework": "Quarkus"},
    {"marker": "pom.xml", "content_check": "micronaut", "framework": "Micronaut"},
    {"marker": "pom.xml", "content_check": None, "framework": "Maven"},
    {"marker": "build.gradle", "content_check": "spring", "framework": "Spring Boot"},
    {"marker": "build.gradle", "content_check": "quarkus", "framework": "Quarkus"},
    {"marker": "build.gradle", "content_check": None, "framework": "Gradle"},
    {"marker": "build.gradle.kts", "content_check": "spring", "framework": "Spring Boot"},
    {"marker": "build.gradle.kts", "content_check": None, "framework": "Gradle (Kotlin)"},
    # Go
    {"marker": "go.mod", "content_check": "gin-gonic", "framework": "Gin"},
    {"marker": "go.mod", "content_check": "fiber", "framework": "Fiber"},
    {"marker": "go.mod", "content_check": "echo", "framework": "Echo"},
    {"marker": "go.mod", "content_check": "chi", "framework": "Chi"},
    {"marker": "go.mod", "content_check": None, "framework": "Go Module"},
    # Ruby
    {"marker": "Gemfile", "content_check": "rails", "framework": "Ruby on Rails"},
    {"marker": "Gemfile", "content_check": "sinatra", "framework": "Sinatra"},
    {"marker": "config.ru", "content_check": None, "framework": "Rack"},
    # PHP
    {"marker": "artisan", "content_check": None, "framework": "Laravel"},
    {"marker": "composer.json", "content_check": "laravel", "framework": "Laravel"},
    {"marker": "composer.json", "content_check": "symfony", "framework": "Symfony"},
    {"marker": "composer.json", "content_check": None, "framework": "Composer"},
    # Rust
    {"marker": "Cargo.toml", "content_check": "actix", "framework": "Actix Web"},
    {"marker": "Cargo.toml", "content_check": "axum", "framework": "Axum"},
    {"marker": "Cargo.toml", "content_check": "rocket", "framework": "Rocket"},
    {"marker": "Cargo.toml", "content_check": None, "framework": "Cargo"},
    # C# / .NET
    {"marker": "Program.cs", "content_check": None, "framework": "ASP.NET"},
    # Elixir
    {"marker": "mix.exs", "content_check": "phoenix", "framework": "Phoenix"},
    {"marker": "mix.exs", "content_check": None, "framework": "Mix"},
    # Dart
    {"marker": "pubspec.yaml", "content_check": "flutter", "framework": "Flutter"},
    {"marker": "pubspec.yaml", "content_check": None, "framework": "Dart"},
]


class LanguageDetector:
    """Detect programming language and framework from a source directory."""

    def _inspect_package_json(self, pkg_path: Path) -> tuple[str, list[str]]:
        """Parse package.json dependencies and identify the primary framework."""
        if not pkg_path.exists():
            return "Unknown", []

        try:
            content = pkg_path.read_text(encoding="utf-8", errors="ignore")
            data = json.loads(content)
            deps = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }
            dep_names = {k.lower() for k in deps.keys()}

            # High priority backend frameworks
            if "fastify" in dep_names or any(k.startswith("@fastify/") for k in dep_names):
                return "Fastify", ["package.json"]
            if "@nestjs/core" in dep_names or "nest" in dep_names:
                return "NestJS", ["package.json"]
            if "express" in dep_names:
                return "Express.js", ["package.json"]
            if "koa" in dep_names:
                return "Koa", ["package.json"]
            if "@hapi/hapi" in dep_names or "hapi" in dep_names:
                return "Hapi", ["package.json"]
            if "hono" in dep_names:
                return "Hono", ["package.json"]
            if "elysia" in dep_names:
                return "Elysia", ["package.json"]
            if "@adonisjs/core" in dep_names or any(k.startswith("@adonisjs/") for k in dep_names):
                return "AdonisJS", ["package.json"]

            # Full-stack / SSR / meta frameworks
            if "next" in dep_names:
                return "Next.js", ["package.json"]
            if "nuxt" in dep_names or "nuxt3" in dep_names:
                return "Nuxt.js", ["package.json"]
            if any(k.startswith("@remix-run/") for k in dep_names):
                return "Remix", ["package.json"]
            if "astro" in dep_names:
                return "Astro", ["package.json"]
            if "@sveltejs/kit" in dep_names or "svelte" in dep_names:
                return "SvelteKit", ["package.json"]
            if "@angular/core" in dep_names:
                return "Angular", ["package.json"]
            if "solid-js" in dep_names:
                return "SolidJS", ["package.json"]

            # Frontend frameworks / builders
            if "vite" in dep_names:
                return "Vite", ["package.json"]
            if "react" in dep_names:
                return "React", ["package.json"]
            if "vue" in dep_names:
                return "Vue.js", ["package.json"]

        except Exception as e:
            logger.debug("package_json_parse_error", error=str(e))

        return "Unknown", []

    def detect(self, source_dir: str) -> dict[str, Any]:
        """Analyze a source directory and return language/framework detection results.

        Args:
            source_dir: Path to the cloned repository or source code.

        Returns:
            {
                "primary_language": str,
                "framework": str,
                "framework_category": str,           # node_backend, node_frontend, python, go, etc.
                "languages_found": dict[str, int],  # language → file count
                "confidence": str,                   # "high", "medium", "low"
                "marker_files": list[str],           # framework indicator files found
            }
        """
        root = Path(source_dir)
        if not root.exists():
            return {
                "primary_language": "Unknown",
                "framework": "Unknown",
                "framework_category": "other",
                "languages_found": {},
                "confidence": "low",
                "marker_files": [],
            }

        # Count files by language extension
        lang_counts: dict[str, int] = {}
        total_files = 0

        for file_path in root.rglob("*"):
            # Skip hidden dirs, node_modules, vendor, .git, venv, etc.
            parts = file_path.parts
            if any(
                p.startswith(".")
                or p
                in (
                    "node_modules",
                    "vendor",
                    "__pycache__",
                    "venv",
                    ".venv",
                    "dist",
                    "build",
                    "target",
                    ".git",
                )
                for p in parts
            ):
                continue

            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in EXTENSION_MAP:
                    lang = EXTENSION_MAP[ext]
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1
                    total_files += 1

        # Determine primary language
        primary_language = "Unknown"
        if lang_counts:
            primary_language = max(lang_counts, key=lang_counts.get)  # type: ignore[arg-type]

        # Detect framework
        framework = "Unknown"
        marker_files: list[str] = []

        # 1. First priority for Node/JS/TS: Direct structured package.json inspection
        pkg_json_path = root / "package.json"
        if pkg_json_path.exists():
            parsed_fw, parsed_markers = self._inspect_package_json(pkg_json_path)
            if parsed_fw != "Unknown":
                framework = parsed_fw
                marker_files.extend(parsed_markers)

        # 2. Config file and marker heuristics
        if framework == "Unknown":
            for marker in FRAMEWORK_MARKERS:
                marker_path = root / marker["marker"]
                if marker_path.exists():
                    if marker["content_check"] is None:
                        # File existence alone is enough
                        framework = marker["framework"]
                        marker_files.append(marker["marker"])
                        break
                    else:
                        # Check file content for the dependency/keyword
                        try:
                            content = (
                                marker_path.read_text(encoding="utf-8", errors="ignore").lower()
                            )
                            if marker["content_check"].lower() in content:
                                framework = marker["framework"]
                                marker_files.append(marker["marker"])
                                break
                        except OSError:
                            continue

        # Determine framework category
        framework_category = self.get_framework_category(framework, primary_language)

        # Determine confidence
        confidence = "low"
        if framework != "Unknown" and primary_language != "Unknown":
            confidence = "high"
        elif primary_language != "Unknown":
            confidence = "medium"

        result = {
            "primary_language": primary_language,
            "framework": framework,
            "framework_category": framework_category,
            "languages_found": lang_counts,
            "confidence": confidence,
            "marker_files": marker_files,
        }

        logger.info(
            "language_detection_complete",
            primary_language=primary_language,
            framework=framework,
            framework_category=framework_category,
            confidence=confidence,
            total_source_files=total_files,
        )

        return result

    def get_framework_category(self, framework: str, primary_language: str) -> str:
        """Classify detected stack into operational category for Dockerfile generation."""
        if framework in NODE_BACKEND_FRAMEWORKS:
            return "node_backend"
        if framework in NODE_FRONTEND_FRAMEWORKS:
            return "node_frontend"
        if framework in PYTHON_FRAMEWORKS or primary_language == "Python":
            return "python"
        if framework in GO_FRAMEWORKS or primary_language == "Go":
            return "go"
        if framework in JAVA_FRAMEWORKS or primary_language in ("Java", "Kotlin"):
            return "java"
        if framework in RUST_FRAMEWORKS or primary_language == "Rust":
            return "rust"
        if framework in PHP_FRAMEWORKS or primary_language == "PHP":
            return "php"
        if framework in RUBY_FRAMEWORKS or primary_language == "Ruby":
            return "ruby"
        if framework in DOTNET_FRAMEWORKS or primary_language == "C#":
            return "dotnet"
        if primary_language in (
            "JavaScript",
            "TypeScript",
            "JavaScript (React)",
            "TypeScript (React)",
        ):
            # Default JS/TS projects without frontend marker are treated as Node backend services
            return "node_backend"
        return "other"

    def get_display_string(self, detection: dict[str, Any]) -> str:
        """Format detection result as 'Language / Framework' display string."""
        lang = detection.get("primary_language", "Unknown")
        framework = detection.get("framework", "Unknown")
        if framework != "Unknown":
            return f"{lang} / {framework}"
        return lang


# Global singleton
language_detector = LanguageDetector()
