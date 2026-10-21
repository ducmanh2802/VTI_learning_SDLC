"""Health endpoints (FR-222).

`live` tells whether the process answers; `ready` tells whether the service
can serve data, that is whether Postgres and Redis answer within 2 seconds.
"""

from fastapi import APIRouter, Request

from analytics.api.deps import app_settings
from analytics.api.errors import ApiError, FieldError
from analytics.api.schemas import HealthStatus, LiveResponse, ReadyComponents, ReadyResponse
from analytics.common.errors import ErrorCode
from analytics.common.health import check_postgres, check_redis

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LiveResponse)
async def live() -> LiveResponse:
    """Return `UP` as soon as the process is able to answer."""
    return LiveResponse(status=HealthStatus.UP)


@router.get("/health/ready", response_model=ReadyResponse)
async def ready(request: Request) -> ReadyResponse:
    """Return `UP` only when Postgres and Redis both answer."""
    settings = app_settings(request)
    results = [
        await check_postgres(settings.analytics_db_url),
        await check_redis(settings.redis_url),
    ]
    unhealthy = [result for result in results if not result.healthy]
    if unhealthy:
        names = ", ".join(result.name for result in unhealthy)
        raise ApiError(
            status_code=503,
            code=ErrorCode.DATA_STALE,
            detail=f"Component not ready: {names}",
            errors=[FieldError(field=result.name, message=result.detail) for result in unhealthy],
        )
    return ReadyResponse(
        status=HealthStatus.UP,
        components=ReadyComponents(db=HealthStatus.UP, redis=HealthStatus.UP),
    )
