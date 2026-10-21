"""Application factory of the internal API."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from analytics.api.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from analytics.api.middleware import CorrelationIdMiddleware, RequestLogMiddleware
from analytics.api.routes.health import router as health_router
from analytics.api.routes.protected import build_protected_router
from analytics.common.config import Settings, get_settings
from analytics.common.logging import configure_logging

INTERNAL_PREFIX = "/internal/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the internal API application.

    Every route lives under `/internal/v1`. Health routes are public inside
    the internal network, every other route needs the service token.
    """
    resolved = settings or get_settings()
    configure_logging(resolved.log_level)

    app = FastAPI(
        title="Analytics internal API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = resolved

    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health_router, prefix=INTERNAL_PREFIX)
    app.include_router(
        build_protected_router(include_probe=resolved.env == "test"), prefix=INTERNAL_PREFIX
    )
    return app
