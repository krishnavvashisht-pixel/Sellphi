from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.company import CompanySource, CompanyStatus, CompanyType, FundingStage, OwnershipType


class CompanyCreate(BaseModel):
    workspace_id: UUID
    mission_id: UUID | None = None

    name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    # Either/both may be supplied; CompanyService normalizes them into a
    # consistent (website, domain) pair — see _normalize_web_presence.
    website: str | None = Field(default=None, max_length=2048)
    domain: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=2048)

    industry: str | None = Field(default=None, max_length=255)
    sub_industry: str | None = Field(default=None, max_length=255)
    company_size: str | None = Field(default=None, max_length=64)
    annual_revenue: float | None = Field(default=None, ge=0)

    headquarters_country: str | None = Field(default=None, max_length=128)
    headquarters_state: str | None = Field(default=None, max_length=128)
    headquarters_city: str | None = Field(default=None, max_length=128)
    founded_year: int | None = Field(default=None, ge=1600, le=2100)

    company_type: CompanyType | None = None
    ownership_type: OwnershipType | None = None
    stock_symbol: str | None = Field(default=None, max_length=16)
    funding_stage: FundingStage | None = None

    technologies: list[str] = Field(default_factory=list)

    description: str | None = Field(default=None, max_length=20_000)
    summary: str | None = Field(default=None, max_length=5_000)

    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    health_score: int | None = Field(default=None, ge=0, le=100)
    fit_score: int | None = Field(default=None, ge=0, le=100)
    engagement_score: int | None = Field(default=None, ge=0, le=100)
    confidence_score: int | None = Field(default=None, ge=0, le=100)

    source: CompanySource = CompanySource.MANUAL

    # Accepted directly for now; in a later sprint this should come from the
    # authenticated request context rather than the request body.
    created_by: UUID | None = None

    @field_validator("name", "legal_name", "industry", "sub_industry")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class CompanyUpdate(BaseModel):
    """
    `status` and `source` are excluded — status changes only through the
    dedicated /archive and /restore actions (and the service-only `qualify`),
    and source describes provenance, which shouldn't change after creation.
    """

    mission_id: UUID | None = None

    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=2048)
    domain: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=2048)

    industry: str | None = Field(default=None, max_length=255)
    sub_industry: str | None = Field(default=None, max_length=255)
    company_size: str | None = Field(default=None, max_length=64)
    annual_revenue: float | None = Field(default=None, ge=0)

    headquarters_country: str | None = Field(default=None, max_length=128)
    headquarters_state: str | None = Field(default=None, max_length=128)
    headquarters_city: str | None = Field(default=None, max_length=128)
    founded_year: int | None = Field(default=None, ge=1600, le=2100)

    company_type: CompanyType | None = None
    ownership_type: OwnershipType | None = None
    stock_symbol: str | None = Field(default=None, max_length=16)
    funding_stage: FundingStage | None = None

    technologies: list[str] | None = None

    description: str | None = Field(default=None, max_length=20_000)
    summary: str | None = Field(default=None, max_length=5_000)

    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None

    health_score: int | None = Field(default=None, ge=0, le=100)
    fit_score: int | None = Field(default=None, ge=0, le=100)
    engagement_score: int | None = Field(default=None, ge=0, le=100)
    confidence_score: int | None = Field(default=None, ge=0, le=100)

    @field_validator("name", "legal_name", "industry", "sub_industry")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class CompanyResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    mission_id: UUID | None

    name: str
    legal_name: str | None
    website: str | None
    domain: str | None
    linkedin_url: str | None

    industry: str | None
    sub_industry: str | None
    company_size: str | None
    annual_revenue: float | None

    headquarters_country: str | None
    headquarters_state: str | None
    headquarters_city: str | None
    founded_year: int | None

    company_type: CompanyType | None
    ownership_type: OwnershipType | None
    stock_symbol: str | None
    funding_stage: FundingStage | None

    technologies: list[str]

    description: str | None
    summary: str | None

    tags: list[str]
    metadata: dict[str, Any] = Field(validation_alias="metadata_", serialization_alias="metadata")

    health_score: int | None
    fit_score: int | None
    engagement_score: int | None
    confidence_score: int | None

    status: CompanyStatus
    source: CompanySource

    created_by: UUID | None

    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CompanyListResponse(BaseModel):
    items: list[CompanyResponse]
    total: int
    offset: int
    limit: int
