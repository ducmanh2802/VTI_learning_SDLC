"""Test only route used to check the service token authentication.

It is registered only when the service runs with `ENV=test`, so it never
exists in dev or production.
"""

from fastapi import APIRouter

router = APIRouter(tags=["test"])


@router.get("/_auth-probe")
async def auth_probe(count: int | None = None) -> dict[str, object]:
    """Return a small payload once the caller proved it holds the token."""
    return {"status": "ok", "count": count}
