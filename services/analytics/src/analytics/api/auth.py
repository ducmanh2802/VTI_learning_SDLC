"""Service token authentication.

The internal API is only reachable from the internal Docker network and every
call must carry the shared secret in the `X-Service-Token` header
(NFR-S06, SDD 3.6.2).
"""

import hmac

from fastapi import Header, HTTPException, Request, status

from analytics.api.deps import app_settings


def tokens_match(candidate: str, expected: str) -> bool:
    """Compare two tokens in constant time."""
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))


async def require_service_token(
    request: Request,
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
) -> None:
    """Reject the request when the service token is missing or wrong."""
    settings = app_settings(request)
    expected = settings.service_token.get_secret_value()
    if not x_service_token or not tokens_match(x_service_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
            headers={"WWW-Authenticate": "ServiceToken"},
        )
