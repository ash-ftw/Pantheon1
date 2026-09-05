"""Route Broker Reverse Proxy Router — PRD §7.5 / Module 11 (Phase 8).

Provides human-accessible, destination-locked reverse proxy endpoints (/r/{route_id})
bridging browser requests to the internal target service with:
1. Dynamic Route State Validation (403 on revoked/disabled)
2. Strict Server-Side TTL Validation (410 on expired)
3. Zero-SSRF Destination Locking (destination resolved strictly from DB)
4. Framing Header Stripping for secure UI previewing
"""

import os
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.logging import get_logger
from app.models import Route

logger = get_logger(__name__)

router = APIRouter(prefix="/r", tags=["route-proxy"])


async def _resolve_route(route_id_str: str, db: AsyncSession) -> Route:
    """Resolve and validate route state strictly from database."""
    clean_id = route_id_str.strip()

    # Try full UUID first
    try:
        val_uuid = uuid.UUID(clean_id)
        res = await db.execute(select(Route).where(Route.id == val_uuid))
        route = res.scalar_one_or_none()
    except ValueError:
        # Prefix match on UUID string (e.g. 8-char prefix '56002f75')
        res = await db.execute(select(Route).where(cast(Route.id, String).startswith(clean_id)))
        route = res.scalars().first()

    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route '{clean_id}' not found in registry.",
        )

    # 1. State check: Revocation check (Tier 1 instant deny)
    if route.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Route disabled / revoked: {route.revocation_reason or 'Kill switch engaged'}",
        )

    # 2. Server-Side TTL check
    now = datetime.now(UTC)
    if now > route.expires_at or route.status == "expired":
        if route.status != "expired":
            route.status = "expired"
            db.add(route)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Route expired: TTL exceeded (PRD §7.5).",
        )

    if route.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Route is not active (status: {route.status}).",
        )

    return route


def _rewrite_urls_in_html(content: bytes, route_id_str: str, content_type: str | None) -> bytes:
    """Rewrite absolute-path URLs in HTML so they route through /r/{route_id}/...

    Handles:
      - <meta http-equiv="refresh" content="1;url=/login?from=...">
      - href="/...", src="/...", action="/..."
      - Location-style references embedded in JS redirects
    """
    if not content_type or "text/html" not in content_type:
        return content

    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        return content

    import re

    proxy_base = f"/r/{route_id_str}"

    # Rewrite meta refresh: url=/path → url=/r/{id}/path
    text = re.sub(
        r'(url=)(/[^"\'\s>]+)',
        lambda m: f"{m.group(1)}{proxy_base}{m.group(2)}",
        text,
        flags=re.IGNORECASE,
    )

    # Rewrite href="/...", src="/...", action="/..."
    text = re.sub(
        r'((?:href|src|action)\s*=\s*["\'])(/[^"\']*)',
        lambda m: f"{m.group(1)}{proxy_base}{m.group(2)}",
        text,
        flags=re.IGNORECASE,
    )

    # Rewrite JS redirect patterns: redirect-url='/path'
    text = re.sub(
        r'(data-redirect-url\s*=\s*["\'])(/[^"\']*)',
        lambda m: f"{m.group(1)}{proxy_base}{m.group(2)}",
        text,
        flags=re.IGNORECASE,
    )

    return text.encode("utf-8")


async def _proxy_to_target(
    route: Route,
    subpath: str,
    request: Request,
) -> Response:
    """Reverse proxy request to the destination-locked target service.

    Key behaviors:
    - Does NOT follow redirects server-side; rewrites Location headers instead
    - Rewrites HTML body so relative URLs route through /r/{route_id}/
    """
    target_host = os.getenv("PANTHEON_TARGET_HOST", "localhost")
    target_port = route.target_port
    route_id_short = str(route.id)[:8]

    # Clean path concatenation
    prefix = (route.path_prefix or "/").strip("/")
    clean_sub = subpath.strip("/")
    if prefix and clean_sub:
        combined_path = f"{prefix}/{clean_sub}"
    elif prefix:
        combined_path = prefix
    else:
        combined_path = clean_sub

    target_url = f"http://{target_host}:{target_port}/{combined_path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    # Filter incoming request headers
    forward_headers = dict(request.headers)
    forward_headers.pop("host", None)
    forward_headers.pop("content-length", None)
    # Request uncompressed content from upstream so httpx receives raw text/assets
    # without unsupported encodings (Brotli 'br' / 'zstd')
    forward_headers["accept-encoding"] = "identity"

    try:
        body = await request.body()
        # Do NOT follow redirects — we rewrite Location headers instead
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=forward_headers,
                content=body if body else None,
            )

            # Strip restrictive framing headers so preview renders cleanly in UI
            resp_headers = {
                k: v
                for k, v in resp.headers.items()
                if k.lower()
                not in (
                    "x-frame-options",
                    "content-security-policy",
                    "content-security-policy-report-only",
                    "transfer-encoding",
                    "content-encoding",
                    "content-length",
                )
            }

            # Rewrite Location header for redirects (301/302/303/307/308)
            if "location" in resp_headers:
                loc = resp_headers["location"]
                # Absolute-path redirect from target (e.g. /login?from=%2F)
                if loc.startswith("/"):
                    resp_headers["location"] = f"/r/{route_id_short}{loc}"
                # Full URL pointing back to the target origin
                elif loc.startswith(f"http://{target_host}:{target_port}"):
                    path_part = loc.split(f"http://{target_host}:{target_port}", 1)[1]
                    resp_headers["location"] = f"/r/{route_id_short}{path_part}"

            # Inject CORS headers
            resp_headers["access-control-allow-origin"] = "*"
            resp_headers["access-control-allow-methods"] = "*"
            resp_headers["access-control-allow-headers"] = "*"
            resp_headers["x-pantheon-route-id"] = str(route.id)

            # Rewrite HTML body URLs for meta-refresh / href / src patterns
            content_type = resp.headers.get("content-type", "")
            rewritten_body = _rewrite_urls_in_html(resp.content, route_id_short, content_type)

            return Response(
                content=rewritten_body,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type"),
                headers=resp_headers,
            )

    except httpx.ConnectError:
        # Service unreachable fallback
        fallback_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Pantheon Route Proxy — Service Offline</title>
    <style>
        body {{ background: #07090d; color: #e2e8f0; font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; }}
        .card {{ background: #0d1117; border: 1px solid #f59e0b; padding: 40px; border-radius: 16px; max-width: 520px; box-shadow: 0 10px 30px rgba(245,158,11,0.15); }}
        h2 {{ color: #f59e0b; margin-top: 0; }}
        p {{ color: #94a3b8; font-size: 13px; line-height: 1.6; }}
        .badge {{ display: inline-block; background: rgba(0,212,170,0.15); color: #00d4aa; padding: 4px 10px; border-radius: 6px; font-family: monospace; font-size: 12px; margin-top: 8px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>⚡ Route Active — Target Waiting</h2>
        <p>The ephemeral route <strong>{str(route.id)[:8]}</strong> is <strong>ACTIVE</strong>, but target service <code>{route.target_service}</code> on port <code>{target_port}</code> is not responding yet.</p>
        <p>Make sure the application container is started from the <strong>App Onboarding</strong> page.</p>
        <div class="badge">Target: {route.target_service}:{target_port} ({route.namespace})</div>
    </div>
</body>
</html>"""
        return Response(content=fallback_html, status_code=200, media_type="text/html")
    except Exception as err:
        logger.warning("route_proxy_error", route_id=str(route.id), error=str(err))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Route proxy connection error: {err!s}",
        )


@router.api_route(
    "/{route_id}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
)
async def route_proxy_root(
    route_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Proxy root path of destination-locked route."""
    route = await _resolve_route(route_id, db)
    return await _proxy_to_target(route, "", request)


@router.api_route(
    "/{route_id}/{subpath:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def route_proxy_subpath(
    route_id: str,
    subpath: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Proxy sub-path of destination-locked route."""
    route = await _resolve_route(route_id, db)
    return await _proxy_to_target(route, subpath, request)
