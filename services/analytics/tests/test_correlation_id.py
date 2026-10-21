"""Correlation id handling (SDD 3.6.4)."""

from uuid import UUID

import httpx

LIVE_PATH = "/internal/v1/health/live"


async def test_correlation_id_is_echoed(client: httpx.AsyncClient) -> None:
    correlation_id = "11111111-2222-3333-4444-555555555555"

    response = await client.get(LIVE_PATH, headers={"X-Correlation-Id": correlation_id})

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == correlation_id


async def test_invalid_correlation_id_is_replaced(client: httpx.AsyncClient) -> None:
    response = await client.get(LIVE_PATH, headers={"X-Correlation-Id": "not-a-uuid"})

    assert response.status_code == 200
    echoed = response.headers["X-Correlation-Id"]
    assert echoed != "not-a-uuid"
    assert str(UUID(echoed)) == echoed


async def test_correlation_id_is_generated_when_missing(client: httpx.AsyncClient) -> None:
    response = await client.get(LIVE_PATH)

    assert response.status_code == 200
    echoed = response.headers["X-Correlation-Id"]
    assert str(UUID(echoed)) == echoed


async def test_problem_document_carries_the_correlation_id(client: httpx.AsyncClient) -> None:
    correlation_id = "99999999-8888-7777-6666-555555555555"

    response = await client.get(
        "/internal/v1/_auth-probe", headers={"X-Correlation-Id": correlation_id}
    )

    assert response.status_code == 401
    assert response.json()["correlationId"] == correlation_id
