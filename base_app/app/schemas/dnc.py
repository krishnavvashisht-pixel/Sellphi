from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DncCreate(BaseModel):
    domain: str = Field(min_length=3, max_length=255)
    company_name: str | None = None
    reason: str = Field(default="Competitor", pattern="^(Competitor|Current Customer|Opt-Out|Partner|Other)$")


class DncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domain: str
    company_name: str | None = None
    reason: str | None = None
    added_by: str | None = None
    created_at: datetime
