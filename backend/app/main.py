"""Pantheon Backend — FastAPI application entry point.

Phase 0: Empty app with /health endpoint.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.logging import get_logger, setup_logging
from app.middleware import RequestContextMiddleware
from app.routers import (
    apps,
    attack_graph,
    auth,
    defence,
    discovery,
    infrastructure,
    observability,
    orgs,
    route_proxy,
    routes,
    safety,
    scenarios,
    test_runs,
)

logger = get_logger(__name__)

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle manager."""
    setup_logging()
    logger.info(
        "pantheon_backend_starting",
        environment=settings.app_env.value,
        debug=settings.app_debug,
    )
    try:
        from app.database import Base, engine

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.warning("auto_db_init_warning", error=str(e))

    yield
    logger.info("pantheon_backend_shutting_down")


app = FastAPI(
    title="Pantheon API",
    description="B2B Security Testing Platform — Deploy Your App, Attack It Safely",
    version="0.1.0",
    lifespan=lifespan,
)

# Slowapi state & error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler))

# CORS — configurable via settings, permissive for LAN and development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request context middleware
app.add_middleware(RequestContextMiddleware)

# Routers
app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(infrastructure.router)
app.include_router(apps.router)
app.include_router(discovery.router)
app.include_router(scenarios.router)
app.include_router(safety.router)
app.include_router(routes.router)
app.include_router(route_proxy.router)
app.include_router(test_runs.router)
app.include_router(attack_graph.router)
app.include_router(defence.router)
app.include_router(observability.router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "pantheon-api"}
