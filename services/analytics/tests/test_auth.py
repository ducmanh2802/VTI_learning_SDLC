"""Service token authentication (NFR-S06)."""

import httpx

PROBE_PATH = "/internal/v1/_auth-probe"


async def test_probe_without_token_is_unauthenticated(client: httpx.AsyncClient) -> None:
    response = await client.get(PROBE_PATH)

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "UNAUTHENTICATED"
    assert body["status"] == 401
    assert body["correlationId"]
    assert "Traceback" not in response.text


async def test_probe_with_a_wrong_token_is_unauthenticated(
    client: httpx.AsyncClient, service_token: str
) -> None:
    response = await client.get(PROBE_PATH, headers={"X-Service-Token": service_token + "x"})

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


async def test_probe_with_an_empty_token_is_unauthenticated(client: httpx.AsyncClient) -> None:
    response = await client.get(PROBE_PATH, headers={"X-Service-Token": ""})

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


async def test_probe_with_the_right_token_is_allowed(
    client: httpx.AsyncClient, service_token: str
) -> None:
    response = await client.get(PROBE_PATH, headers={"X-Service-Token": service_token})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
