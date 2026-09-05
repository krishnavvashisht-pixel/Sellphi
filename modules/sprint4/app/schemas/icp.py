from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ICPCreate(BaseModel):
    product_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)

    # Company size targeting
    employee_range_min: int | None = Field(default=None, ge=0)
    employee_range_max: int | None = Field(default=None, ge=0)

    # Revenue targeting (in USD)
    annual_revenue_min: int | None = Field(default=None, ge=0)
    annual_revenue_max: int | None = Field(default=None, ge=0)

    # Geographic targeting
    countries: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)

    # Industry & technology signals
    industries: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    funding_stages: list[str] = Field(default_factory=list)
    growth_signals: list[str] = Field(default_factory=list)

    # Keyword targeting
    keywords: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)

    # Scoring configuration
    scoring_rules: dict[str, Any] = Field(default_factory=dict)

    # State flags
    is_default: bool = False
    is_active: bool = True

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def validate_ranges(self) -> "ICPCreate":
        _validate_range(
            self.employee_range_min,
            self.employee_range_max,
            "employee_range_min",
            "employee_range_max",
        )
        _validate_range(
            self.annual_revenue_min,
            self.annual_revenue_max,
            "annual_revenue_min",
            "annual_revenue_max",
        )
        return self


class ICPUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)

    employee_range_min: int | None = Field(default=None, ge=0)
    employee_range_max: int | None = Field(default=None, ge=0)

    annual_revenue_min: int | None = Field(default=None, ge=0)
    annual_revenue_max: int | None = Field(default=None, ge=0)

    countries: list[str] | None = None
    states: list[str] | None = None
    cities: list[str] | None = None

    industries: list[str] | None = None
    technologies: list[str] | None = None
    funding_stages: list[str] | None = None
    growth_signals: list[str] | None = None

    keywords: list[str] | None = None
    negative_keywords: list[str] | None = None

    scoring_rules: dict[str, Any] | None = None

    is_default: bool | None = None
    is_active: bool | None = None

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def validate_ranges(self) -> "ICPUpdate":
        _validate_range(
            self.employee_range_min,
            self.employee_range_max,
            "employee_range_min",
            "employee_range_max",
        )
        _validate_range(
            self.annual_revenue_min,
            self.annual_revenue_max,
            "annual_revenue_min",
            "annual_revenue_max",
        )
        return self


class ICPResponse(BaseModel):
    id: UUID
    product_id: UUID
    name: str
    description: str | None

    employee_range_min: int | None
    employee_range_max: int | None
    annual_revenue_min: int | None
    annual_revenue_max: int | None

    countries: list[str]
    states: list[str]
    cities: list[str]

    industries: list[str]
    technologies: list[str]
    funding_stages: list[str]
    growth_signals: list[str]

    keywords: list[str]
    negative_keywords: list[str]

    scoring_rules: dict[str, Any]

    is_default: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ICPListResponse(BaseModel):
    items: list[ICPResponse]
    total: int
    offset: int
    limit: int


# ── Private helper ────────────────────────────────────────────────────────────

def _validate_range(
    min_val: int | None,
    max_val: int | None,
    min_field: str,
    max_field: str,
) -> None:
    if min_val is not None and max_val is not None and min_val > max_val:
        raise ValueError(f"{min_field} must be less than or equal to {max_field}")
