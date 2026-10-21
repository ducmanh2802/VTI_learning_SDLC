"""Correlation id and request logging middleware."""

import logging
import time
from uuid import UUID, uuid4

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from analytics.common.logging import reset_correlation_id, set_correlation_id

logger = logging.getLogger("analytics.api.request")

CORRELATION_ID_HEADER = "x-correlation-id"


def resolve_correlation_id(raw: str | None) -> str:
    """Return the correlation id of a request, replacing an invalid one."""
    if raw:
        try:
            return str(UUID(raw.strip()))
        except ValueError:
            logger.warning("invalid correlation id header, replaced with a new one")
    return str(uuid4())


class CorrelationIdMiddleware:
    """Bind a correlation id to the request and echo it in the response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        correlation_id = resolve_correlation_id(headers.get(CORRELATION_ID_HEADER))
        token = set_correlation_id(correlation_id)

        async def send_with_correlation_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                raw_headers = message.setdefault("headers", [])
                raw_headers.append((CORRELATION_ID_HEADER.encode(), correlation_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation_id)
        finally:
            reset_correlation_id(token)


class RequestLogMiddleware:
    """Write one JSON log line per request, with the correlation id."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        status_code = 500

        async def send_with_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", 500))
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "request",
                extra={
                    "method": scope.get("method", ""),
                    "path": scope.get("path", ""),
                    "status": status_code,
                    "durationMs": duration_ms,
                },
            )
