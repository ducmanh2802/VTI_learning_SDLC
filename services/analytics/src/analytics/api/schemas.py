"""Payload models of the health endpoints.

They mirror `HealthLive` and `Health` of the internal contract. The models
generated from `contracts/openapi/dist/internal.yaml` live in
`analytics.api.models_generated`.
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


class ReadyComponents(BaseModel):
    """Health of each dependency."""

    db: HealthStatus
    redis: HealthStatus


class ReadyResponse(BaseModel):
    """Payload of `GET /internal/v1/health/ready`."""

    status: HealthStatus
    components: ReadyComponents
