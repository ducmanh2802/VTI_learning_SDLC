"""ASGI entry point: `uvicorn analytics.api.main:app`."""

from analytics.api.app import create_app

app = create_app()
