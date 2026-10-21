"""JSON logging with a correlation id carried in a context variable.

Every line is one JSON object with at least `ts`, `level`, `service`,
`correlationId` and `msg` (SDD 3.6.4). The correlation id is stored in a
`ContextVar`, so any coroutine running inside a request sees the same value
without passing it around.
"""

import logging
import sys
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any, TextIO

import orjson

SERVICE_NAME = "analytics"
LOG_FIELDS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    """Return the correlation id of the current context, if any."""
    return _correlation_id.get()


def set_correlation_id(value: str) -> Token[str | None]:
    """Bind a correlation id to the current context and return the reset token."""
    return _correlation_id.set(value)


def reset_correlation_id(token: Token[str | None]) -> None:
    """Restore the correlation id that was bound before the matching `set`."""
    _correlation_id.reset(token)


class JsonFormatter(logging.Formatter):
    """Render a log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "correlationId": getattr(record, "correlation_id", None)
            or get_correlation_id()
            or None,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in LOG_FIELDS or key.startswith("_") or key == "correlation_id":
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return orjson.dumps(payload, default=str).decode("utf-8")


class JsonStreamHandler(logging.StreamHandler[TextIO]):
    """Stream handler owned by this module; used to avoid duplicated output.

    The stream is resolved on every record, so the handler follows the
    current `sys.stdout` (useful when the output is captured or redirected).
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Write the record to the current standard output."""
        self.stream = sys.stdout
        super().emit(record)


def configure_logging(level: str = "INFO") -> None:
    """Send every log record to stdout as JSON.

    Handlers installed by other tools (pytest, for instance) are kept; only
    the handlers installed by this function are replaced, so calling it twice
    does not duplicate the output.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        if isinstance(handler, JsonStreamHandler):
            root.removeHandler(handler)

    handler = JsonStreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True
