from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SavedSearchCreate(BaseModel):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=500)
    region: str = Field(default="IN", max_length=10)
    limit: int = Field(default=5, ge=1, le=10)


class SavedSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    query: str
    region: str
    limit: int
    created_at: datetime
