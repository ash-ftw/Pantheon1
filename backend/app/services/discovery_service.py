"""Discovery Service - PRD Modules 5-6 (Phase 5).

Target Analysis: profiles deployed apps (language, framework, ports, DB, auth).
Endpoint Discovery: probes OpenAPI/Swagger specs and classifies endpoints.

All discovery happens from within the tenant namespace — never from the
range cluster — and is labeled as discovery, not an attack (FR-3.4).
"""

import os
import uuid
from typing import Any

import httpx

try:
    from prance import ResolvingParser  # type: ignore[import-untyped]
except ImportError:
    ResolvingParser = None


from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory
from app.logging import get_logger
from app.models import App, AppVersion
from app.services.k8s_service import k8s_tenant_service

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_app_exposed_port(target_profile: dict[str, Any] | None) -> int:
    """Return the accessible port from the target profile, preferring host_port if mapped locally."""
    if target_profile:
        if target_profile.get("host_port"):
            return int(target_profile["host_port"])
        if target_profile.get("exposed_ports"):
            return target_profile["exposed_ports"][0]
    return 8085


# ---------------------------------------------------------------------------
# Target Analysis
# ---------------------------------------------------------------------------


async def run_target_analysis(app_id: uuid.UUID, org_id: uuid.UUID) -> dict[str, Any]:
    """Profile a deployed app: language, framework, ports, DB, auth.

    Merges data from:
    1. AppVersion.detected_framework (captured during ingestion)
    2. K8s introspection (image names, container ports, env vars)

    Returns a profile dict with confidence scoring.
    """
    namespace = k8s_tenant_service.get_namespace_name(org_id)

    profile: dict[str, Any] = {
        "app_id": str(app_id),
        "org_id": str(org_id),
        "namespace": namespace,
        "discovery_status": "completed",
        "language": None,
        "framework": None,
        "exposed_ports": [],
        "detected_db": None,
        "db_environment_variables": [],
        "auth_mechanisms": [],
        "auth_env_variables": [],
        "confidence": "low",
        "confidence_basis": "",
    }

    confidence_signals: list[str] = []

    # --- Step 1: Pull ingestion metadata from DB (highest confidence source) ---
    try:
        async with async_session_factory() as db:
            res = await db.execute(
                select(AppVersion)
                .where(AppVersion.app_id == app_id)
                .order_by(AppVersion.version_number.desc())
            )
            latest_version = res.scalars().first()

            if latest_version and latest_version.detected_framework:
                fw = latest_version.detected_framework
                # Parse "Language / Framework", "Language (Framework)", or "Language" format
                if " / " in fw:
                    parts = fw.split(" / ", 1)
                    profile["language"] = parts[0].strip().lower()
                    profile["framework"] = parts[1].strip().lower()
                elif "/" in fw:
                    parts = fw.split("/", 1)
                    profile["language"] = parts[0].strip().lower()
                    profile["framework"] = parts[1].strip().lower()
                elif "(" in fw:
                    parts = fw.split("(", 1)
                    profile["language"] = parts[0].strip().lower()
                    profile["framework"] = parts[1].rstrip(")").strip().lower()
                else:
                    profile["language"] = fw.strip().lower()

                confidence_signals.append("ingestion-detected-framework")
    except Exception as e:
        logger.warning("discovery_db_read_error", error=str(e))

    # --- Step 2: K8s introspection ---
    has_k8s = k8s_tenant_service._get_client()

    if not has_k8s or not k8s_tenant_service._core_api or not k8s_tenant_service._apps_api:
        # Simulated profile for offline / mock mode
        if not profile["language"]:
            profile["language"] = "python"
            profile["framework"] = "fastapi"
        profile["exposed_ports"] = profile["exposed_ports"] or [8080]
        profile["detected_db"] = profile["detected_db"] or "postgresql"
        profile["db_environment_variables"] = profile["db_environment_variables"] or [
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
        ]
        profile["auth_mechanisms"] = profile["auth_mechanisms"] or ["oauth2"]
        profile["auth_env_variables"] = profile["auth_env_variables"] or [
            "AUTH_SECRET",
            "JWT_SECRET",
        ]
        confidence_signals.append("simulated-mode")
        profile["confidence"] = "low"
        profile["confidence_basis"] = "Simulated mode — no K8s cluster connected"
        return profile

    # Query deployments for exposed ports & image info
    try:
        deps = k8s_tenant_service._apps_api.list_namespaced_deployment(namespace=namespace)
        for d in deps.items:
            container = (
                d.spec.template.spec.containers[0] if d.spec.template.spec.containers else None
            )
            image = container.image if container else None

            # Detect language/framework from image tag if not already known from ingestion
            if image and not profile["language"]:
                profile = _detect_language_framework(image, profile)
                if profile["language"]:
                    confidence_signals.append("k8s-image-heuristic")

            # Collect container ports
            for c in d.spec.template.spec.containers or []:
                for port in c.ports or []:
                    if port.container_port not in profile["exposed_ports"]:
                        profile["exposed_ports"].append(port.container_port)
    except Exception as e:
        logger.warning("target_analysis_deploy_read_error", error=str(e))

    # Query services for port mapping
    try:
        svcs = k8s_tenant_service._core_api.list_namespaced_service(namespace=namespace)
        for s in svcs.items:
            for p in s.spec.ports or []:
                if p.port not in profile["exposed_ports"]:
                    profile["exposed_ports"].append(p.port)
    except Exception as e:
        logger.warning("target_analysis_service_read_error", error=str(e))

    if profile["exposed_ports"]:
        confidence_signals.append("k8s-port-discovery")

    # Check environment variables for DB and auth detection
    try:
        pods = k8s_tenant_service._core_api.list_namespaced_pod(namespace=namespace)
        db_env_keys = {
            "db_host",
            "db_port",
            "db_name",
            "db_user",
            "db_password",
            "db_suffix",
            "postgres_host",
            "postgres_port",
            "postgres_db",
            "mysql_host",
            "mysql_port",
            "mongo_host",
            "mongo_port",
            "pg_host",
            "pg_port",
            "database_url",
            "database_host",
            "redis_url",
            "redis_host",
        }
        auth_env_keys = {
            "auth_secret",
            "jwt_secret",
            "api_key",
            "auth_token",
            "oauth_secret",
            "private_key",
            "session_secret",
            "jwt_private_key_path",
            "jwt_public_key_path",
        }

        found_db_env: set[str] = set()
        found_auth_env: set[str] = set()

        for p in pods.items:
            for container in p.spec.containers or []:
                for env_var in container.env or []:
                    key_lower = (env_var.name or "").lower()
                    if key_lower in db_env_keys:
                        found_db_env.add(env_var.name)
                    if key_lower in auth_env_keys:
                        found_auth_env.add(env_var.name)

        profile["db_environment_variables"] = sorted(found_db_env)
        profile["auth_env_variables"] = sorted(found_auth_env)

        # Derive detected_db from env var patterns
        db_lower = {e.lower() for e in found_db_env}
        if any(k in db_lower for k in ("postgres_host", "pg_host", "database_url")):
            profile["detected_db"] = "postgresql"
        elif any(k in db_lower for k in ("mysql_host",)):
            profile["detected_db"] = "mysql"
        elif any(k in db_lower for k in ("mongo_host",)):
            profile["detected_db"] = "mongodb"
        elif any(k in db_lower for k in ("redis_url", "redis_host")):
            profile["detected_db"] = "redis"
        elif found_db_env:
            profile["detected_db"] = "database"

        if found_db_env:
            confidence_signals.append("k8s-env-db-detection")

        # Derive auth_mechanisms from env var names
        if found_auth_env:
            auth_lower = {e.lower() for e in found_auth_env}
            if any(k in auth_lower for k in ("jwt_secret", "jwt_private_key_path")):
                profile["auth_mechanisms"] = ["jwt"]
            elif "oauth_secret" in auth_lower:
                profile["auth_mechanisms"] = ["oauth2"]
            elif "api_key" in auth_lower:
                profile["auth_mechanisms"] = ["api_key"]
            elif "session_secret" in auth_lower:
                profile["auth_mechanisms"] = ["session"]
            else:
                profile["auth_mechanisms"] = ["unknown"]
            confidence_signals.append("k8s-env-auth-detection")
        else:
            profile["auth_mechanisms"] = ["none detected"]

    except Exception as e:
        logger.warning("target_analysis_env_read_error", error=str(e))

    # Compute overall confidence
    if len(confidence_signals) >= 3:
        profile["confidence"] = "high"
    elif len(confidence_signals) >= 1:
        profile["confidence"] = "medium"
    else:
        profile["confidence"] = "low"
    profile["confidence_basis"] = (
        ", ".join(confidence_signals) if confidence_signals else "no signals"
    )

    return profile


def _detect_language_framework(image: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Heuristic language/framework detection from Docker image name."""
    img = image.lower()
    if any(k in img for k in ("python", "fastapi", "uvicorn", "django", "flask")):
        profile["language"] = "python"
        if "fastapi" in img or "uvicorn" in img:
            profile["framework"] = "fastapi"
        elif "django" in img:
            profile["framework"] = "django"
        elif "flask" in img:
            profile["framework"] = "flask"
        else:
            profile["framework"] = "unknown"
    elif any(k in img for k in ("node", "express", "next")):
        profile["language"] = "javascript"
        if "express" in img or "next" in img:
            profile["framework"] = "express"
        else:
            profile["framework"] = "unknown"
    elif any(k in img for k in ("java", "openjdk", "spring")):
        profile["language"] = "java"
        if "spring" in img:
            profile["framework"] = "spring boot"
        else:
            profile["framework"] = "unknown"
    elif any(k in img for k in ("ruby", "rails", "ror")):
        profile["language"] = "ruby"
        profile["framework"] = "ror"
    elif "golang" in img or "go:" in img or "go-" in img:
        profile["language"] = "go"
        profile["framework"] = "unknown"
    elif any(k in img for k in ("php", "laravel", "symfony")):
        profile["language"] = "php"
        if "laravel" in img:
            profile["framework"] = "laravel"
        elif "symfony" in img:
            profile["framework"] = "symfony"
        else:
            profile["framework"] = "unknown"
    return profile


# ---------------------------------------------------------------------------
# Endpoint Discovery
# ---------------------------------------------------------------------------

# Extended list of common OpenAPI/Swagger paths to probe
_COMMON_SPEC_PATHS = [
    "/openapi.json",
    "/swagger.json",
    "/api-docs",
    "/docs",
    "/v1/api-docs",
    "/swagger/v1/swagger.json",
    "/api/v1/openapi.json",
    "/api/openapi.json",
    "/api/swagger.json",
    "/swagger-ui/api-docs",
]


async def discover_endpoints(app_id: uuid.UUID, org_id: uuid.UUID) -> dict[str, Any]:
    """Probe common OpenAPI/Swagger paths on the deployed app.

    Extracts endpoints, methods, parameters and classifies them:
      - public
      - likely_admin
      - likely_auth
      - upload
      - search

    Each endpoint gets a confidence score and basis.
    """
    namespace = k8s_tenant_service.get_namespace_name(org_id)

    profile: dict[str, Any] = {
        "app_id": str(app_id),
        "org_id": str(org_id),
        "namespace": namespace,
        "discovery_status": "completed",
        "specs_found": [],
        "endpoints": [],
        "classification": {
            "public": [],
            "likely_admin": [],
            "likely_auth": [],
            "upload": [],
            "search": [],
        },
    }

    # Determine the host and port to probe (network-readiness / K8s / container)
    port = 8085
    probe_host = os.getenv("PANTHEON_TARGET_HOST") or getattr(
        settings, "target_probe_host", "localhost"
    )
    app_obj = None
    try:
        async with async_session_factory() as db:
            res = await db.execute(select(App).where(App.id == app_id))
            app_obj = res.scalar_one_or_none()
            if app_obj and app_obj.target_profile:
                port = _get_app_exposed_port(app_obj.target_profile)
                if app_obj.target_profile.get("probe_host"):
                    probe_host = app_obj.target_profile["probe_host"]
    except Exception as e:
        logger.warning("discovery_port_lookup_error", error=str(e))

    # Try httpx probing first (works with or without prance)
    for path in _COMMON_SPEC_PATHS:
        full_url = f"http://{probe_host}:{port}{path}"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(full_url)
                if resp.status_code == 200:
                    content_type = resp.headers.get("content-type", "")
                    if "json" in content_type or "yaml" in content_type:
                        spec = resp.json()
                        if "paths" in spec or "openapi" in spec or "swagger" in spec:
                            profile["specs_found"].append(path)
                            _extract_endpoints_from_spec(spec, profile)
                            logger.info(
                                "endpoint_discovery_spec_found",
                                path=path,
                                host=probe_host,
                                port=port,
                                endpoint_count=len(profile["endpoints"]),
                            )
                            break  # Found a valid spec, stop probing
        except Exception as e:
            logger.debug("endpoint_discovery_probe_failed", path=full_url, error=str(e))
            continue

    # Fallback: try prance ResolvingParser if no spec found via httpx
    if not profile["specs_found"] and ResolvingParser is not None:
        for path in _COMMON_SPEC_PATHS[:3]:
            full_url = f"http://{probe_host}:{port}{path}"
            try:
                parser = ResolvingParser(full_url, store_schema=False)
                spec = parser.spec
                if spec:
                    profile["specs_found"].append(path)
                    _extract_endpoints_from_spec(spec, profile)
                    break
            except Exception as e:
                logger.debug("prance_parse_failed", path=path, error=str(e))
                continue

    # Fallback: preset demo application spec detection if probe yielded no spec
    if not profile["specs_found"] and app_obj:
        from app.services.demo_workloads import get_demo_openapi_spec, match_demo_app_key

        app_name = getattr(app_obj, "name", None)
        if isinstance(app_name, str):
            app_url = getattr(app_obj, "source_url", None)
            demo_key = match_demo_app_key(app_name, app_url if isinstance(app_url, str) else None)
            if demo_key:
                demo_spec = get_demo_openapi_spec(demo_key)
                if demo_spec:
                    profile["specs_found"].append("/openapi.json")
                    _extract_endpoints_from_spec(demo_spec, profile)
                    logger.info(
                        "endpoint_discovery_preset_spec_applied",
                        demo_key=demo_key,
                        endpoint_count=len(profile["endpoints"]),
                    )

    return profile


def _extract_endpoints_from_spec(spec: dict, profile: dict[str, Any]) -> None:
    """Extract and classify endpoints from an OpenAPI/Swagger spec."""
    if "paths" not in spec:
        return

    for route_path, methods in spec["paths"].items():
        if not isinstance(methods, dict):
            continue

        for method, details in methods.items():
            if method not in ("get", "post", "put", "delete", "patch", "head", "options"):
                continue
            if not isinstance(details, dict):
                continue

            classification = _classify_endpoint(route_path, method, details)
            confidence, basis = _compute_classification_confidence(
                route_path, method, details, classification
            )

            endpoint_info = {
                "path": route_path,
                "method": method.upper(),
                "summary": details.get("summary", ""),
                "description": details.get("description", ""),
                "classification": classification,
                "confidence": confidence,
                "confidence_basis": basis,
                "parameters": details.get("parameters", []),
            }
            profile["endpoints"].append(endpoint_info)

            # Add to classification buckets
            bucket = profile["classification"].setdefault(classification, [])
            bucket.append(endpoint_info)


def _classify_endpoint(path: str, method: str, details: dict) -> str:
    """Classify a single endpoint based on path and method patterns."""
    path_lower = path.lower()
    summary_lower = (details.get("summary") or "").lower()
    description_lower = (details.get("description") or "").lower()

    # Upload detection
    if any(
        kw in path_lower or kw in summary_lower or kw in description_lower
        for kw in ["upload", "file", "attach", "avatar", "image", "photo"]
    ):
        return "upload"

    # Search detection
    if any(
        kw in path_lower or kw in summary_lower or kw in description_lower
        for kw in ["search", "query", "filter", "find"]
    ):
        return "search"

    # Likely admin paths
    admin_kw = ["admin", "manage", "delete", "drop", "configure", "settings"]
    if any(kw in path_lower or kw in summary_lower for kw in admin_kw):
        return "likely_admin"

    # Likely auth endpoints
    auth_kw = ["login", "logout", "auth", "token", "signup", "signin", "credentials", "register"]
    if any(kw in path_lower or kw in summary_lower for kw in auth_kw):
        return "likely_auth"

    # Default to public
    return "public"


def _compute_classification_confidence(
    path: str, method: str, details: dict, classification: str
) -> tuple[str, str]:
    """Compute confidence level and basis string for an endpoint classification."""
    path_lower = path.lower()
    reasons: list[str] = []

    # Path-based signals are stronger
    if classification == "likely_auth":
        auth_kw = ["login", "logout", "auth", "token", "signup", "signin", "register"]
        matched = [kw for kw in auth_kw if kw in path_lower]
        if matched:
            reasons.append(f"path contains '{', '.join(matched)}'")
    elif classification == "likely_admin":
        admin_kw = ["admin", "manage", "settings"]
        matched = [kw for kw in admin_kw if kw in path_lower]
        if matched:
            reasons.append(f"path contains '{', '.join(matched)}'")
    elif classification == "upload":
        upload_kw = ["upload", "file", "attach"]
        matched = [kw for kw in upload_kw if kw in path_lower]
        if matched:
            reasons.append(f"path contains '{', '.join(matched)}'")
    elif classification == "search":
        search_kw = ["search", "query", "filter", "find"]
        matched = [kw for kw in search_kw if kw in path_lower]
        if matched:
            reasons.append(f"path contains '{', '.join(matched)}'")

    # Check summary/description for additional signals
    summary = (details.get("summary") or "").lower()
    if summary:
        reasons.append("summary metadata present")

    # Security scheme signals
    security = details.get("security", [])
    if security:
        reasons.append("security scheme declared")

    # Compute confidence from signal count
    if len(reasons) >= 2:
        confidence = "high"
    elif len(reasons) == 1:
        confidence = "medium"
    else:
        confidence = "low"
        reasons.append("default classification")

    return confidence, "; ".join(reasons)
