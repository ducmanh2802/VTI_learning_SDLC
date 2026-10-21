"""Health endpoints (FR-222)."""

import httpx
import pytest

from analytics.api.app import create_app
from analytics.common.config import Settings


async def test_live_is_up(client: httpx.AsyncClient) -> None:
    response = await client.get("/internal/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


async def test_live_needs_no_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/internal/v1/health/live")

    assert response.status_code == 200


async def test_ready_is_up_when_both_dependencies_answer(
    database_url: str, redis_url: str, service_token: str
) -> None:
    app = create_app(
        Settings(
            analytics_db_url=database_url,
            redis_url=redis_url,
            service_token=service_token,
            env="test",
        )
    )
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://analytics.test") as client:
        response = await client.get("/internal/v1/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "UP"
    assert body["components"] == {"db": "UP", "redis": "UP"}


async def test_ready_is_503_when_redis_is_unreachable(
    database_url: str, service_token: str
) -> None:
    app = create_app(
        Settings(
            analytics_db_url=database_url,
            redis_url="redis://127.0.0.1:1/0",
            service_token=service_token,
            env="test",
        )
    )
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://analytics.test") as client:
        response = await client.get("/internal/v1/health/ready")

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "DATA_STALE"
    assert body["status"] == 503
    failing = [error["field"] for error in body["errors"]]
    assert failing == ["redis"]


async def test_ready_is_503_when_postgres_is_unreachable(
    redis_url: str, service_token: str
) -> None:
    app = create_app(
        Settings(
            analytics_db_url="postgresql+asyncpg://analytics:secret@127.0.0.1:1/vnstockai",
            redis_url=redis_url,
            service_token=service_token,
            env="test",
        )
    )
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://analytics.test") as client:
        response = await client.get("/internal/v1/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "DATA_STALE"
    assert [error["field"] for error in body["errors"]] == ["db"]
    assert "secret" not in response.text


@pytest.mark.parametrize("path", ["/internal/v1/health/live", "/internal/v1/health/ready"])
async def test_health_routes_live_under_the_internal_prefix(
    client: httpx.AsyncClient, path: str
) -> None:
    response = await client.get(path)

    assert response.status_code in (200, 503)
    assert response.url.path == path


async def test_probe_route_is_absent_outside_the_test_environment(service_token: str) -> None:
    app = create_app(
        Settings(
            analytics_db_url="postgresql+asyncpg://analytics:secret@127.0.0.1:1/vnstockai",
            redis_url="redis://127.0.0.1:1/0",
            service_token=service_token,
            env="dev",
        )
    )
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://analytics.test") as client:
        response = await client.get(
            "/internal/v1/_auth-probe", headers={"X-Service-Token": service_token}
        )

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
