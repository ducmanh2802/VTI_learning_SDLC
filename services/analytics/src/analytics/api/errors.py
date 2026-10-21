"""RFC 9457 problem responses.

Every error leaving the internal API is an `application/problem+json` document
with a stable `code` (SDD 3.6.1). Unexpected exceptions never leak a stack
trace to the caller; the traceback stays in the log.
"""

import logging
from uuid import uuid4

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from analytics.common.errors import ERROR_TYPE_PREFIX, ErrorCode
from analytics.common.logging import get_correlation_id

logger = logging.getLogger("analytics.api.errors")

PROBLEM_MEDIA_TYPE = "application/problem+json"

_TITLES: dict[ErrorCode, str] = {
    ErrorCode.VALIDATION_ERROR: "Invalid request",
    ErrorCode.UNAUTHENTICATED: "Unauthenticated",
    ErrorCode.TOKEN_REUSED: "Token reused",
    ErrorCode.TERMS_NOT_ACCEPTED: "Terms not accepted",
    ErrorCode.DERIVATIVE_RISK_NOT_ACKED: "Derivative risk not acknowledged",
    ErrorCode.INVITE_INVALID: "Invalid invite",
    ErrorCode.FORBIDDEN: "Forbidden",
    ErrorCode.NOT_FOUND: "Not found",
    ErrorCode.LIMIT_EXCEEDED: "Limit exceeded",
    ErrorCode.RISK_LOT_SIZE: "Invalid lot size",
    ErrorCode.RISK_PRICE_BAND: "Price outside the allowed band",
    ErrorCode.RISK_TICK_SIZE: "Invalid tick size",
    ErrorCode.RISK_INSUFFICIENT_CASH: "Insufficient cash",
    ErrorCode.RISK_INSUFFICIENT_SHARES: "Insufficient shares",
    ErrorCode.RISK_SESSION: "Outside the trading session",
    ErrorCode.RISK_ORDER_LIMIT: "Order limit exceeded",
    ErrorCode.RISK_DAILY_LIMIT: "Daily limit exceeded",
    ErrorCode.RISK_HALTED: "Trading halted",
    ErrorCode.DATA_STALE: "Data unavailable",
    ErrorCode.AI_QUOTA_EXCEEDED: "AI quota exceeded",
    ErrorCode.RATE_LIMITED: "Rate limited",
    ErrorCode.ACCOUNT_LOCKED: "Account locked",
    ErrorCode.INTERNAL_ERROR: "Internal error",
}

_STATUS_TO_CODE: dict[int, ErrorCode] = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.UNAUTHENTICATED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.LIMIT_EXCEEDED,
    422: ErrorCode.VALIDATION_ERROR,
    423: ErrorCode.ACCOUNT_LOCKED,
    429: ErrorCode.RATE_LIMITED,
    500: ErrorCode.INTERNAL_ERROR,
    503: ErrorCode.DATA_STALE,
}


class FieldError(BaseModel):
    """One field level error of a problem document."""

    field: str
    message: str


class Problem(BaseModel):
    """RFC 9457 problem document."""

    model_config = ConfigDict(populate_by_name=True)

    type: str
    title: str
    status: int
    detail: str
    code: str
    correlation_id: str = Field(alias="correlationId")
    errors: list[FieldError] | None = None


class ApiError(Exception):
    """Error raised by the service, carrying its problem document."""

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        detail: str,
        *,
        title: str | None = None,
        errors: list[FieldError] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.title = title or _TITLES.get(code, "Error")
        self.errors = errors


def build_problem(
    *,
    status_code: int,
    code: ErrorCode,
    detail: str,
    title: str | None = None,
    errors: list[FieldError] | None = None,
) -> Problem:
    """Build the problem document of an error."""
    slug = code.value.lower().replace("_", "-")
    return Problem(
        type=f"{ERROR_TYPE_PREFIX}{slug}",
        title=title or _TITLES.get(code, "Error"),
        status=status_code,
        detail=detail,
        code=code.value,
        correlationId=get_correlation_id() or str(uuid4()),
        errors=errors,
    )


def problem_response(problem: Problem) -> JSONResponse:
    """Render a problem document as an HTTP response."""
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(mode="json", by_alias=True, exclude_none=True),
        media_type=PROBLEM_MEDIA_TYPE,
    )


async def api_error_handler(request: object, exc: Exception) -> JSONResponse:
    """Render an `ApiError` raised by the service."""
    if not isinstance(exc, ApiError):
        raise exc
    return problem_response(
        build_problem(
            status_code=exc.status_code,
            code=exc.code,
            detail=exc.detail,
            title=exc.title,
            errors=exc.errors,
        )
    )


async def http_exception_handler(request: object, exc: Exception) -> JSONResponse:
    """Render an `HTTPException` as a problem document."""
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    status_code = exc.status_code
    code = _STATUS_TO_CODE.get(status_code, ErrorCode.INTERNAL_ERROR)
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    response = problem_response(build_problem(status_code=status_code, code=code, detail=detail))
    if exc.headers:
        response.headers.update(exc.headers)
    return response


async def validation_exception_handler(request: object, exc: Exception) -> JSONResponse:
    """Render a request validation error as a `VALIDATION_ERROR` problem."""
    errors: list[FieldError] = []
    if isinstance(exc, RequestValidationError):
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc", ()))
            errors.append(
                FieldError(field=location or "body", message=str(error.get("msg", "invalid")))
            )
    return problem_response(
        build_problem(
            status_code=400,
            code=ErrorCode.VALIDATION_ERROR,
            detail="Request validation failed",
            errors=errors,
        )
    )


async def unhandled_exception_handler(request: object, exc: Exception) -> JSONResponse:
    """Render an unexpected exception as an `INTERNAL_ERROR` problem."""
    logger.error("unhandled error", exc_info=exc)
    return problem_response(
        build_problem(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            detail="Internal server error",
        )
    )
