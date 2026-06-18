from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

HealthState = Literal["ok", "degraded", "error"]


class ComponentHealth(BaseModel):
    name: str = Field(min_length=1)
    status: HealthState
    detail: str = Field(min_length=1)


class HealthResponse(BaseModel):
    service: str = Field(min_length=1)
    status: HealthState
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    components: list[ComponentHealth] = Field(default_factory=list)
