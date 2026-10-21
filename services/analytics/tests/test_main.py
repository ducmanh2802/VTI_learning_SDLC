"""ASGI entry point of the internal API."""

from analytics.api import main


def test_the_entry_point_builds_an_application() -> None:
    paths = main.app.openapi()["paths"]

    assert "/internal/v1/health/live" in paths
    assert "/internal/v1/health/ready" in paths
