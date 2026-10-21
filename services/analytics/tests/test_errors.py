"""RFC 9457 error format."""

import httpx
from fastapi import FastAPI

PROBE_PATH = "/internal/v1/_auth-probe"


async def test_validation_error_is_a_400_problem(
    client: httpx.AsyncClient, service_token: str
) -> None:
    response = await client.get(
        PROBE_PATH, headers={"X-Service-Token": service_token}, params={"count": "not-a-number"}
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["status"] == 400
    assert body["type"].startswith("/errors/")
    assert body["title"]
    assert body["errors"][0]["field"] == "query.count"


async def test_unhandled_error_is_a_500_problem_without_a_traceback(
    app: FastAPI, service_token: str
) -> None:
    @app.get("/internal/v1/_boom")
    async def boom() -> None:
        raise RuntimeError("secret internal detail")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://analytics.test") as client:
        response = await client.get("/internal/v1/_boom")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert body["status"] == 500
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text


async def test_unknown_route_is_a_404_problem(client: httpx.AsyncClient) -> None:
    response = await client.get("/internal/v1/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["status"] == 404
