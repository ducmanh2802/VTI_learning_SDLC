"""Application settings, loaded from the environment.

Every knob of the Analytics service comes from an environment variable so the
same image can run in dev, CI and production without code changes.
"""

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ANALYTICS_DB_URL = (
    "postgresql+asyncpg://analytics_svc:change-me-analytics@postgres:5432/vnstockai"
)
DEFAULT_REDIS_URL = "redis://:change-me-redis@redis:6379/0"
MIN_SERVICE_TOKEN_LENGTH = 32
ALLOWED_LOG_LEVELS = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"})


class Settings(BaseSettings):
    """Runtime configuration of the Analytics service."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=None,
        extra="ignore",
        case_sensitive=False,
        validate_default=True,
    )

    analytics_db_url: str = Field(
        default=DEFAULT_ANALYTICS_DB_URL,
        description="SQLAlchemy async URL of the Postgres instance (schema market/ai/research).",
    )
    redis_url: str = Field(
        default=DEFAULT_REDIS_URL,
        description="Redis URL used for quotes, session state and quotas.",
    )
    service_token: SecretStr = Field(
        default=SecretStr(""),
        description="Shared secret presented by Core in the X-Service-Token header.",
    )
    log_level: str = Field(default="INFO", description="Root log level of the process.")
    env: str = Field(default="dev", description="Runtime environment: dev, test or prod.")

    @field_validator("service_token")
    @classmethod
    def _validate_service_token(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < MIN_SERVICE_TOKEN_LENGTH:
            raise ValueError(
                f"SERVICE_TOKEN must be at least {MIN_SERVICE_TOKEN_LENGTH} characters long"
            )
        return value

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in ALLOWED_LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(ALLOWED_LOG_LEVELS)}")
        return level


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, read from the environment on first use."""
    return Settings()
