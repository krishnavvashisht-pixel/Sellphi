from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.buyer_persona import BuyingRole, InfluenceLevel, PersonaStatus, SeniorityLevel


class BuyerPersonaCreate(BaseModel):
    product_id: UUID
    name: str = Field(min_length=1, max_length=255)
    job_title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)

    # Buying-committee classification
    seniority: SeniorityLevel | None = None
    buying_role: BuyingRole | None = None
    influence_level: InfluenceLevel | None = None
    decision_power: int | None = Field(default=None, ge=1, le=10)

    # Persona intelligence
    responsibilities: list[str] = Field(default_factory=list)
    business_goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)

    # Messaging & content targeting
    preferred_channels: list[str] = Field(default_factory=list)
    preferred_content: list[str] = Field(default_factory=list)
    messaging_themes: list[str] = Field(default_factory=list)

    # Keyword targeting
    keywords: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)

    industry_notes: dict[str, Any] = Field(default_factory=dict)

    # State flags
    is_default: bool = False
    status: PersonaStatus = PersonaStatus.DRAFT

    @field_validator("name", "job_title", "department")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class BuyerPersonaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    job_title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)

    seniority: SeniorityLevel | None = None
    buying_role: BuyingRole | None = None
    influence_level: InfluenceLevel | None = None
    decision_power: int | None = Field(default=None, ge=1, le=10)

    responsibilities: list[str] | None = None
    business_goals: list[str] | None = None
    pain_points: list[str] | None = None
    challenges: list[str] | None = None
    objections: list[str] | None = None

    preferred_channels: list[str] | None = None
    preferred_content: list[str] | None = None
    messaging_themes: list[str] | None = None

    keywords: list[str] | None = None
    negative_keywords: list[str] | None = None

    industry_notes: dict[str, Any] | None = None

    is_default: bool | None = None
    status: PersonaStatus | None = None

    @field_validator("name", "job_title", "department")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class BuyerPersonaResponse(BaseModel):
    id: UUID
    product_id: UUID
    name: str
    job_title: str | None
    department: str | None

    seniority: SeniorityLevel | None
    buying_role: BuyingRole | None
    influence_level: InfluenceLevel | None
    decision_power: int | None

    responsibilities: list[str]
    business_goals: list[str]
    pain_points: list[str]
    challenges: list[str]
    objections: list[str]

    preferred_channels: list[str]
    preferred_content: list[str]
    messaging_themes: list[str]

    keywords: list[str]
    negative_keywords: list[str]

    industry_notes: dict[str, Any]

    is_default: bool
    status: PersonaStatus

    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class BuyerPersonaListResponse(BaseModel):
    items: list[BuyerPersonaResponse]
    total: int
    offset: int
    limit: int
