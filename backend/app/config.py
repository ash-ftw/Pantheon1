"""Application configuration via pydantic-settings.

Reads from environment variables and .env file (local dev only, never committed).
One Settings class as the single source of truth — per pantheon-exact-stack.md §2.
"""

from enum import StrEnum
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Pantheon backend settings.

    All values sourced from env vars; .env file for local dev convenience only.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Database (async PostgreSQL via asyncpg)
    database_url: str = "postgresql+asyncpg://pantheon:pantheon_dev@localhost:5432/pantheon"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO (S3-compatible object storage)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "pantheon-artifacts"

    # Container Registry (registry:2, backed by MinIO S3 storage)
    registry_url: str = "localhost:5000"

    # JWT settings
    jwt_secret: str = "dev-pantheon-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440
    jwt_private_key_path: str = "./keys/jwt_private.pem"
    jwt_public_key_path: str = "./keys/jwt_public.pem"

    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT


settings = Settings()
