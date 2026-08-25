"""Language & Framework Detector — PRD Module 4 Item 10.

File-based language and framework detection using file extension heuristics
and known framework marker files. Replaces the hardcoded "Python / FastAPI"
stub with real detection.
"""

from pathlib import Path
from typing import Any

from app.logging import get_logger

logger = get_logger(__name__)

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
FRAMEWORK_MARKERS: list[dict[str, str]] = [
    # Python
    {"marker": "requirements.txt", "content_check": "fastapi", "framework": "FastAPI"},
    {"marker": "requirements.txt", "content_check": "django", "framework": "Django"},
    {"marker": "requirements.txt", "content_check": "flask", "framework": "Flask"},
    {"marker": "pyproject.toml", "content_check": "fastapi", "framework": "FastAPI"},
    {"marker": "pyproject.toml", "content_check": "django", "framework": "Django"},
    {"marker": "pyproject.toml", "content_check": "flask", "framework": "Flask"},
    {"marker": "Pipfile", "content_check": "fastapi", "framework": "FastAPI"},
    {"marker": "Pipfile", "content_check": "django", "framework": "Django"},
    {"marker": "manage.py", "content_check": None, "framework": "Django"},
    # JavaScript / TypeScript
    {"marker": "next.config.js", "content_check": None, "framework": "Next.js"},
    {"marker": "next.config.mjs", "content_check": None, "framework": "Next.js"},
    {"marker": "next.config.ts", "content_check": None, "framework": "Next.js"},
    {"marker": "nuxt.config.ts", "content_check": None, "framework": "Nuxt.js"},
    {"marker": "nuxt.config.js", "content_check": None, "framework": "Nuxt.js"},
    {"marker": "angular.json", "content_check": None, "framework": "Angular"},
    {"marker": "vite.config.ts", "content_check": None, "framework": "Vite"},
    {"marker": "vite.config.js", "content_check": None, "framework": "Vite"},
    {"marker": "svelte.config.js", "content_check": None, "framework": "SvelteKit"},
    {"marker": "package.json", "content_check": "express", "framework": "Express.js"},
    {"marker": "package.json", "content_check": "nest", "framework": "NestJS"},
    {"marker": "package.json", "content_check": "react", "framework": "React"},
    {"marker": "package.json", "content_check": "vue", "framework": "Vue.js"},
    # Java / JVM
    {"marker": "pom.xml", "content_check": "spring-boot", "framework": "Spring Boot"},
    {"marker": "pom.xml", "content_check": None, "framework": "Maven"},
    {"marker": "build.gradle", "content_check": "spring", "framework": "Spring Boot"},
    {"marker": "build.gradle", "content_check": None, "framework": "Gradle"},
    {"marker": "build.gradle.kts", "content_check": None, "framework": "Gradle (Kotlin)"},
    # Go
    {"marker": "go.mod", "content_check": "gin-gonic", "framework": "Gin"},
    {"marker": "go.mod", "content_check": "fiber", "framework": "Fiber"},
    {"marker": "go.mod", "content_check": "echo", "framework": "Echo"},
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
    {"marker": "Cargo.toml", "content_check": "rocket", "framework": "Rocket"},
    {"marker": "Cargo.toml", "content_check": "axum", "framework": "Axum"},
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

    def detect(self, source_dir: str) -> dict[str, Any]:
        """Analyze a source directory and return language/framework detection results.

        Args:
            source_dir: Path to the cloned repository or source code.

        Returns:
            {
                "primary_language": str,
                "framework": str,
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

        # Detect framework from marker files
        framework = "Unknown"
        marker_files: list[str] = []

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
                        content = marker_path.read_text(encoding="utf-8", errors="ignore").lower()
                        if marker["content_check"].lower() in content:
                            framework = marker["framework"]
                            marker_files.append(marker["marker"])
                            break
                    except OSError:
                        continue

        # Determine confidence
        confidence = "low"
        if framework != "Unknown" and primary_language != "Unknown":
            confidence = "high"
        elif primary_language != "Unknown":
            confidence = "medium"

        result = {
            "primary_language": primary_language,
            "framework": framework,
            "languages_found": lang_counts,
            "confidence": confidence,
            "marker_files": marker_files,
        }

        logger.info(
            "language_detection_complete",
            primary_language=primary_language,
            framework=framework,
            confidence=confidence,
            total_source_files=total_files,
        )

        return result

    def get_display_string(self, detection: dict[str, Any]) -> str:
        """Format detection result as 'Language / Framework' display string."""
        lang = detection.get("primary_language", "Unknown")
        framework = detection.get("framework", "Unknown")
        if framework != "Unknown":
            return f"{lang} / {framework}"
        return lang


# Global singleton
language_detector = LanguageDetector()
