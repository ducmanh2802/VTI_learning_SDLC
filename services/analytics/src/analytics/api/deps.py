"""Dependencies shared by the internal API routes."""

from typing import cast

from fastapi import Request

from analytics.common.config import Settings


def app_settings(request: Request) -> Settings:
    """Return the settings bound to the running application."""
    return cast(Settings, request.app.state.settings)
