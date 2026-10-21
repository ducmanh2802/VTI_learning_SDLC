"""JSON logging (SDD 3.6.4)."""

import json
import logging

import httpx
import pytest

from analytics.common.logging import (
    JsonFormatter,
    get_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)


async def test_a_request_produces_one_json_line_with_the_correlation_id(
    client: httpx.AsyncClient, capsys: pytest.CaptureFixture[str]
) -> None:
    correlation_id = "12341234-5678-5678-5678-567856785678"

    await client.get("/internal/v1/health/live", headers={"X-Correlation-Id": correlation_id})

    captured = capsys.readouterr()
    payloads = [
        json.loads(line) for line in captured.out.splitlines() if line.strip().startswith("{")
    ]
    request_lines = [payload for payload in payloads if payload.get("msg") == "request"]

    assert request_lines
    line = request_lines[0]
    assert line["correlationId"] == correlation_id
    assert line["service"] == "analytics"
    assert line["level"] == "INFO"
    assert line["status"] == 200
    assert line["method"] == "GET"
    assert line["path"] == "/internal/v1/health/live"
    assert line["ts"]


def test_the_formatter_writes_the_expected_fields() -> None:
    record = logging.LogRecord(
        name="analytics.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["service"] == "analytics"
    assert payload["msg"] == "hello"
    assert payload["ts"].endswith("Z")
    assert "correlationId" in payload


def test_the_correlation_id_follows_the_context() -> None:
    assert get_correlation_id() is None

    token = set_correlation_id("abc")
    try:
        assert get_correlation_id() == "abc"
    finally:
        reset_correlation_id(token)

    assert get_correlation_id() is None
