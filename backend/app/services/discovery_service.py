import uuid
from typing import Any, Dict, List, Optional

from fastapi import Request
try:
    from prance import ResolvingParser  # type: ignore[import-untyped]
except ImportError:
    ResolvingParser = None

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.logging import get_logger
from app.services.k8s_service import k8s_tenant_service

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Target Analysis
# ---------------------------------------------------------------------------

async def run_target_analysis(app_id: uuid.UUID, org_id: uuid.UUID) -> Dict[str, Any]:
    """Profile a deployed app: language, framework, ports, DB, auth.

    Scopes all discovery to the org/tenant namespace.
    """
    namespace = k8s_tenant_service.get_namespace_name(org_id)

    # Attempt K8s connection; fall back to simulated data
    has_k8s = k8s_tenant_service._get_client()

    profile: Dict[str, Any] = {
        "app_id": str(app_id),
        "org_id": str(org_id),
        "namespace": namespace,
        "language": None,
        "framework": None,
        "exposed_ports": [],
        "detected_db": None,
        "db_environment_variables": [],
        "auth_mechanisms": [],
        "auth_env_variables": [],
    }

    if not has_k8s or not k8s_tenant_service._core_api or not k8s_tenant_service._apps_api:
        # Simulated profile for offline / mock mode
        profile["language"] = "python"
        profile["framework"] = "fastapi"
        profile["exposed_ports"] = [8080]
        profile["detected_db"] = "postgresql"
        profile["db_environment_variables"] = ["DB_HOST", "DB_PORT", "DB_NAME"]
        profile["auth_mechanisms"] = ["oauth2"]
        profile["auth_env_variables"] = ["AUTH_SECRET", "JWT_SECRET"]
        return profile

    # --- Query deployments for exposed ports & image info ---
    try:
        deps = k8s_tenant_service._apps_api.list_namespaced_deployment(namespace=namespace)
        for d in deps.items:
            container = d.spec.template.spec.containers[0] if d.spec.template.spec.containers else None
            image = container.image if container else None

            # Detect language/framework from image tag / name patterns
            if image:
                profile = _detect_language_framework(image, profile)

            # Collect ports from the deployment's services / container ports
            # We'll also look at services below; for now record container port env hints
            for c in d.spec.template.spec.containers or []:
                for port in c.ports or []:
                    profile["exposed_ports"].append(port.container_port)
    except Exception as e:
        logger.warning("target_analysis_deploy_read_error", error=str(e))

    # --- Query services for port mapping ---
    try:
        svcs = k8s_tenant_service._core_api.list_namespaced_service(namespace=namespace)
        for s in svcs.items:
            for p in s.spec.ports or []:
                profile["exposed_ports"].append(p.port)
    except Exception as e:
        logger.warning("target_analysis_service_read_error", error=str(e))

    # --- Check environment variables for DB and auth detection ---
    try:
        pods = k8s_tenant_service._core_api.list_namespaced_pod(namespace=namespace)
        db_env_keys = {"db_host", "db_port", "db_name", "db_user", "db_password", "db_suffix",
                       "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "MYSQL_HOST", "MYSQL_PORT",
                       "MONGO_HOST", "MONGO_PORT", "PG_HOST", "PG_PORT"}
        auth_env_keys = {"auth_secret", "jwt_secret", "api_key", "auth_token", "oauth_secret",
                         "private_key", "session_secret"}

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
        if "DB_HOST" in found_db_env or "POSTGRES_HOST" in found_db_env or "MYSQL_HOST" in found_db_env or "MONGO_HOST" in found_db_env:
            profile["detected_db"] = "database"
        elif found_db_env:
            profile["detected_db"] = "database"

        # Derive auth_mechanisms from env var names only
        if found_auth_env:
            if "AUTH_SECRET" in found_auth_env or "JWT_SECRET" in found_auth_env:
                profile["auth_mechanisms"] = ["jwt", "oauth2"]
            elif "API_KEY" in found_auth_env:
                profile["auth_mechanisms"] = ["api_key"]
            else:
                profile["auth_mechanisms"] = ["unknown"]
        else:
            profile["auth_mechanisms"] = ["none detected"]

    except Exception as e:
        logger.warning("target_analysis_env_read_error", error=str(e))

    return profile


def _detect_language_framework(image: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    """Heuristic language/framework detection from Docker image name."""
    img = image.lower()
    if "node-" in img or "node:" in img:
        profile["language"] = "javascript"
        if "express" in img or "next" in img:
            profile["framework"] = "express"
        else:
            profile["framework"] = "unknown"
    elif "python" in img:
        profile["language"] = "python"
        if "fastapi" in img or "uvicorn" in img:
            profile["framework"] = "fastapi"
        elif "django" in img:
            profile["framework"] = "django"
        elif "flask" in img:
            profile["framework"] = "flask"
        else:
            profile["framework"] = "unknown"
    elif "java" in img or "openjdk" in img:
        profile["language"] = "java"
        if "spring" in img:
            profile["framework"] = "spring boot"
        else:
            profile["framework"] = "unknown"
    elif "ruby" in img:
        profile["language"] = "ruby"
        profile["framework"] = "ror"
    elif "golang" in img or "go:" in img:
        profile["language"] = "go"
        profile["framework"] = "unknown"
    elif "php" in img:
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

async def discover_endpoints(app_id: uuid.UUID, org_id: uuid.UUID) -> Dict[str, Any]:
    """Probe common OpenAPI/Swagger paths inside the tenant cluster.

    Extracts endpoints, methods, parameters and classifies them:
      - public
      - likely-admin
      - likely-auth
      - upload
      - search
    """
    namespace = k8s_tenant_service.get_namespace_name(org_id)

    profile: Dict[str, Any] = {
        "app_id": str(app_id),
        "org_id": str(org_id),
        "namespace": namespace,
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

    if ResolvingParser is None:
        logger.warning("prance_not_installed_skipping_endpoint_discovery")
        return profile

    # Probe common OpenAPI paths
    common_paths = ["/openapi.json", "/swagger.json", "/api-docs"]

    for path in common_paths:
        try:
            full_url = f"http://localhost:{path}"  # In-cluster would use service DNS
            # For now, attempt ResolvingParser from local file or URL
            # In production this would hit the service endpoint inside the namespace
            parser = ResolvingParser(full_url, store_schema=False)
            spec = parser.spec

            profile["specs_found"].append(path)

            # Extract paths and operations
            if spec and "paths" in spec:
                for route_path, methods in spec["paths"].items():
                    for method, details in methods.items():
                        if method in ("get", "post", "put", "delete", "patch", "head", "options"):
                            endpoint_info = {
                                "path": route_path,
                                "method": method.upper(),
                                "summary": details.get("summary", ""),
                                "description": details.get("description", ""),
                                "parameters": details.get("parameters", []),
                                "responses": details.get("responses", {}),
                            }
                            profile["endpoints"].append(endpoint_info)

                            # Classify the endpoint
                            classification = _classify_endpoint(
                                route_path, method, details
                            )
                            # Add to classification buckets
                            bucket = profile["classification"].setdefault(classification, [])
                            bucket.append(endpoint_info)
        except Exception as e:
            logger.warning("endpoint_discovery_path_failed", path=path, error=str(e))
            continue

    return profile


def _classify_endpoint(path: str, method: str, details: dict) -> str:
    """Classify a single endpoint based on path and method patterns."""
    path_lower = path.lower()
    summary_lower = (details.get("summary") or "").lower()
    description_lower = (details.get("description") or "").lower()

    # Upload detection
    if any(kw in path_lower or kw in summary_lower or kw in description_lower
           for kw in ["upload", "file", "attach", "avatar", "image", "photo"]):
        return "upload"

    # Search detection
    if any(kw in path_lower or kw in summary_lower or kw in description_lower
           for kw in ["search", "query", "filter", "list", "find"]):
        return "search"

    # Likely admin paths
    admin_kw = ["admin", "manage", "delete", "drop", "configure", "settings"]
    if any(kw in path_lower for kw in admin_kw):
        return "likely-admin"

    # Likely auth endpoints
    auth_kw = ["login", "logout", "auth", "token", "signup", "signin", "credentials"]
    if any(kw in path_lower for kw in auth_kw):
        return "likely-auth"

    # Default to public
    return "public"