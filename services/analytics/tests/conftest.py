"""Shared fixtures of the Analytics test suite."""

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import asyncpg
import httpx
import pytest
from fastapi import FastAPI
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

from analytics.api.app import create_app
from analytics.common.config import Settings, get_settings
from analytics.common.health import to_asyncpg_dsn

TEST_SERVICE_TOKEN = "test-service-token-0123456789-0123456789"
REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"

os.environ["SERVICE_TOKEN"] = TEST_SERVICE_TOKEN
os.environ["ENV"] = "test"
os.environ["LOG_LEVEL"] = "INFO"


def apply_migrations(url: str) -> None:
    """Apply every migration of the repository, in order, to a fresh database."""

    async def _apply() -> None:
        connection = await asyncpg.connect(to_asyncpg_dsn(url))
        try:
            for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
                await connection.execute(migration.read_text(encoding="utf-8"))
        finally:
            await connection.close()

    asyncio.run(_apply())


@pytest.fixture
def settings() -> Settings:
    """Return settings built from the test environment."""
    get_settings.cache_clear()
    return Settings()


@pytest.fixture
def service_token() -> str:
    """Return the service token used by the test suite."""
    return TEST_SERVICE_TOKEN


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    """Return the internal API application under test."""
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Return an HTTP client bound to the application under test."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://analytics.test") as client:
        yield client


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """Return the URL of a Postgres container holding the migrated schema."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        url = postgres.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+asyncpg://"
        )
        apply_migrations(url)
        yield url


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    """Return the URL of a Redis container."""
    with RedisContainer("redis:7-alpine") as redis_container:
        host = redis_container.get_container_host_ip()
        port = redis_container.get_exposed_port(6379)
        yield f"redis://{host}:{port}/0"
