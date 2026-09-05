from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.mission import MissionExecutionMode, MissionPriority, MissionStatus


class MissionCreate(BaseModel):
    product_id: UUID
    default_icp_id: UUID | None = None

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    objective: str | None = Field(default=None, max_length=10_000)

    priority: MissionPriority = MissionPriority.MEDIUM
    execution_mode: MissionExecutionMode = MissionExecutionMode.ASSISTED

    daily_prospect_limit: int = Field(default=50, gt=0)
    daily_message_limit: int = Field(default=50, gt=0)
    max_running_agents: int = Field(default=1, gt=0)

    start_date: date | None = None
    end_date: date | None = None
    timezone: str = Field(default="UTC", max_length=64)

    schedule: dict[str, Any] = Field(default_factory=dict)
    filters: dict[str, Any] = Field(default_factory=dict)
    # May include a forward-compatible "buyer_persona_ids": list[str] key, validated
    # against the product's buyer personas by MissionService.
    settings: dict[str, Any] = Field(default_factory=dict)

    # Accepted directly for now; in a later sprint this should come from the
    # authenticated request context rather than the request body.
    created_by: UUID | None = None

    @field_validator("name", "description", "objective")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def validate_date_range(self) -> "MissionCreate":
        _validate_date_range(self.start_date, self.end_date)
        return self


class MissionUpdate(BaseModel):
    """
    Status is intentionally excluded — transitions happen only through the
    dedicated pause/resume/complete/run actions, never via a generic PATCH.
    """

    default_icp_id: UUID | None = None

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    objective: str | None = Field(default=None, max_length=10_000)

    priority: MissionPriority | None = None
    execution_mode: MissionExecutionMode | None = None

    daily_prospect_limit: int | None = Field(default=None, gt=0)
    daily_message_limit: int | None = Field(default=None, gt=0)
    max_running_agents: int | None = Field(default=None, gt=0)

    start_date: date | None = None
    end_date: date | None = None
    timezone: str | None = Field(default=None, max_length=64)

    schedule: dict[str, Any] | None = None
    filters: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None

    @field_validator("name", "description", "objective")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def validate_date_range(self) -> "MissionUpdate":
        # Only checks when both are supplied in the same PATCH; a partial update
        # that only moves one bound is validated against the persisted value by
        # MissionService, which knows the mission's current dates.
        if self.start_date is not None and self.end_date is not None:
            _validate_date_range(self.start_date, self.end_date)
        return self


class MissionResponse(BaseModel):
    id: UUID
    product_id: UUID
    default_icp_id: UUID | None

    name: str
    description: str | None
    objective: str | None

    status: MissionStatus
    priority: MissionPriority
    execution_mode: MissionExecutionMode

    daily_prospect_limit: int
    daily_message_limit: int
    max_running_agents: int

    start_date: date | None
    end_date: date | None
    timezone: str

    schedule: dict[str, Any]
    filters: dict[str, Any]
    settings: dict[str, Any]
    statistics: dict[str, Any]

    last_run_at: datetime | None
    next_run_at: datetime | None

    created_by: UUID | None

    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class MissionListResponse(BaseModel):
    items: list[MissionResponse]
    total: int
    offset: int
    limit: int


# ── Private helper ────────────────────────────────────────────────────────────

def _validate_date_range(start_date: date | None, end_date: date | None) -> None:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date must be less than or equal to end_date")
