"""Pytest configuration and fixtures for Pantheon backend."""

from collections.abc import AsyncGenerator

import pytest

from app.database import engine


@pytest.fixture(autouse=True)
async def cleanup_db_engine() -> AsyncGenerator[None, None]:
    """Dispose connection pool after each test so asyncpg connections don't cross event loops."""
    yield
    await engine.dispose()
