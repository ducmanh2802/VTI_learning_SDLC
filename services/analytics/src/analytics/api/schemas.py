"""Payload models of the internal API.

These models are hand written for the endpoints that exist in R1. The models
generated from `contracts/openapi/dist/internal.yaml` live in
`analytics.api.models_generated` and are added in WP-07 step 4 as soon as the
contract is bundled.
"""

from enum import StrEnum

from pydantic import BaseModel


class HealthStatus(StrEnum):
    """Health of the service or of one of its dependencies."""

    UP = "UP"
    DOWN = "DOWN"


class LiveResponse(BaseModel):
    """Payload of `GET /internal/v1/health/live`."""

    status: HealthStatus


class ComponentStatus(BaseModel):
    """Health of a single dependency."""

    status: HealthStatus
    detail: str | None = None


class ReadyResponse(BaseModel):
    """Payload of `GET /internal/v1/health/ready`."""

    status: HealthStatus
    components: dict[str, ComponentStatus]
