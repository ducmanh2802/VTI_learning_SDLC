"""Dependency probes used by the readiness endpoint.

The probes are fail-closed: any error, timeout or unreachable host makes the
component unhealthy instead of returning a fake value (FR-030).
"""

import asyncio
import contextlib
import re
from dataclasses import dataclass

import asyncpg
from redis.asyncio import Redis

PROBE_TIMEOUT_SECONDS = 2.0
_CREDENTIALS = re.compile(r"://[^/@\s]*:[^/@\s]*@")


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Outcome of a single dependency probe."""

    name: str
    healthy: bool
    detail: str


def _redact(text: str) -> str:
    """Remove credentials from a message before it reaches a log or a response."""
    return _CREDENTIALS.sub("://***:***@", text)


def to_asyncpg_dsn(url: str) -> str:
    """Convert a SQLAlchemy URL into a plain PostgreSQL DSN for asyncpg."""
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix) :]
    return url


async def check_postgres(url: str, timeout_seconds: float = PROBE_TIMEOUT_SECONDS) -> ProbeResult:
    """Run `SELECT 1` against Postgres within the given timeout."""
    try:
        connection = await asyncio.wait_for(
            asyncpg.connect(to_asyncpg_dsn(url)), timeout=timeout_seconds
        )
    except Exception as exc:  # the probe must never raise
        return ProbeResult("db", False, _redact(f"{type(exc).__name__}: {exc}"))

    try:
        await asyncio.wait_for(connection.execute("SELECT 1"), timeout=timeout_seconds)
    except Exception as exc:  # the probe must never raise
        return ProbeResult("db", False, _redact(f"{type(exc).__name__}: {exc}"))
    finally:
        with contextlib.suppress(Exception):
            await connection.close()
    return ProbeResult("db", True, "ok")


async def check_redis(url: str, timeout_seconds: float = PROBE_TIMEOUT_SECONDS) -> ProbeResult:
    """Send `PING` to Redis within the given timeout."""
    client = Redis.from_url(
        url, socket_connect_timeout=timeout_seconds, socket_timeout=timeout_seconds
    )
    try:
        await asyncio.wait_for(client.ping(), timeout=timeout_seconds)
    except Exception as exc:  # the probe must never raise
        return ProbeResult("redis", False, _redact(f"{type(exc).__name__}: {exc}"))
    finally:
        with contextlib.suppress(Exception):
            await client.aclose()
    return ProbeResult("redis", True, "ok")
