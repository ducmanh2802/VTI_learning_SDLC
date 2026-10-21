"""Router of the routes that need the service token.

Every route of the internal API except the health ones goes through this
router, so no new route can be added without the `X-Service-Token` check.
"""

from fastapi import APIRouter, Depends

from analytics.api.auth import require_service_token
from analytics.api.routes.probe import router as probe_router


def build_protected_router(include_probe: bool = False) -> APIRouter:
    """Build the protected router, optionally with the test only probe route."""
    router = APIRouter(dependencies=[Depends(require_service_token)])
    if include_probe:
        router.include_router(probe_router)
    return router
