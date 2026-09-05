from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.workspace import WorkspacePlan, WorkspaceStatus


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    plan: WorkspacePlan = WorkspacePlan.FREE
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "slug")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    plan: WorkspacePlan | None = None
    status: WorkspaceStatus | None = None
    settings: dict[str, Any] | None = None

    @field_validator("name", "slug")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: WorkspacePlan
    status: WorkspaceStatus
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
