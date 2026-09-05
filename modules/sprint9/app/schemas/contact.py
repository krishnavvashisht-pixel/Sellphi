import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.buyer_persona import BuyingRole, SeniorityLevel
from app.models.contact import ContactSource, ContactStatus, PreferredChannel, RelationshipStatus

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email_format(value: str) -> str:
    if not _EMAIL_RE.match(value):
        raise ValueError(f"'{value}' is not a valid email address")
    return value


class ContactCreate(BaseModel):
    company_id: UUID
    buyer_persona_id: UUID | None = None

    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    # If omitted, ContactService derives it from first_name + last_name.
    full_name: str | None = Field(default=None, max_length=511)
    preferred_name: str | None = Field(default=None, max_length=255)

    job_title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    seniority: SeniorityLevel | None = None
    buying_role: BuyingRole | None = None

    email: str | None = Field(default=None, max_length=320)
    alternate_emails: list[str] = Field(default_factory=list)
    phone: str | None = Field(default=None, max_length=64)
    mobile: str | None = Field(default=None, max_length=64)
    linkedin_url: str | None = Field(default=None, max_length=2048)
    twitter_url: str | None = Field(default=None, max_length=2048)

    location_country: str | None = Field(default=None, max_length=128)
    location_state: str | None = Field(default=None, max_length=128)
    location_city: str | None = Field(default=None, max_length=128)
    timezone: str | None = Field(default=None, max_length=64)

    languages: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)

    influence_score: int | None = Field(default=None, ge=0, le=100)
    engagement_score: int | None = Field(default=None, ge=0, le=100)
    confidence_score: int | None = Field(default=None, ge=0, le=100)

    relationship_status: RelationshipStatus = RelationshipStatus.COLD
    preferred_channel: PreferredChannel | None = None

    last_contacted_at: datetime | None = None
    last_replied_at: datetime | None = None

    notes: str | None = Field(default=None, max_length=20_000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    source: ContactSource = ContactSource.MANUAL

    # Accepted directly for now; in a later sprint this should come from the
    # authenticated request context rather than the request body.
    created_by: UUID | None = None

    @field_validator("first_name", "last_name", "full_name", "preferred_name", "job_title", "department")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return _validate_email_format(value) if value is not None else value

    @field_validator("alternate_emails")
    @classmethod
    def validate_alternate_emails(cls, values: list[str]) -> list[str]:
        return [_validate_email_format(v) for v in values]


class ContactUpdate(BaseModel):
    """`status` and `source` are excluded — status changes only through the
    dedicated /archive and /restore actions (and the service-only `verify`);
    source describes provenance and shouldn't change after creation."""

    buyer_persona_id: UUID | None = None

    first_name: str | None = Field(default=None, min_length=1, max_length=255)
    last_name: str | None = Field(default=None, min_length=1, max_length=255)
    full_name: str | None = Field(default=None, max_length=511)
    preferred_name: str | None = Field(default=None, max_length=255)

    job_title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    seniority: SeniorityLevel | None = None
    buying_role: BuyingRole | None = None

    email: str | None = Field(default=None, max_length=320)
    alternate_emails: list[str] | None = None
    phone: str | None = Field(default=None, max_length=64)
    mobile: str | None = Field(default=None, max_length=64)
    linkedin_url: str | None = Field(default=None, max_length=2048)
    twitter_url: str | None = Field(default=None, max_length=2048)

    location_country: str | None = Field(default=None, max_length=128)
    location_state: str | None = Field(default=None, max_length=128)
    location_city: str | None = Field(default=None, max_length=128)
    timezone: str | None = Field(default=None, max_length=64)

    languages: list[str] | None = None
    skills: list[str] | None = None
    interests: list[str] | None = None

    influence_score: int | None = Field(default=None, ge=0, le=100)
    engagement_score: int | None = Field(default=None, ge=0, le=100)
    confidence_score: int | None = Field(default=None, ge=0, le=100)

    relationship_status: RelationshipStatus | None = None
    preferred_channel: PreferredChannel | None = None

    last_contacted_at: datetime | None = None
    last_replied_at: datetime | None = None

    notes: str | None = Field(default=None, max_length=20_000)
    metadata: dict[str, Any] | None = None

    @field_validator("first_name", "last_name", "full_name", "preferred_name", "job_title", "department")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return _validate_email_format(value) if value is not None else value

    @field_validator("alternate_emails")
    @classmethod
    def validate_alternate_emails(cls, values: list[str] | None) -> list[str] | None:
        return [_validate_email_format(v) for v in values] if values is not None else values


class ContactResponse(BaseModel):
    id: UUID
    company_id: UUID
    buyer_persona_id: UUID | None

    first_name: str
    last_name: str
    full_name: str
    preferred_name: str | None

    job_title: str | None
    department: str | None
    seniority: SeniorityLevel | None
    buying_role: BuyingRole | None

    email: str | None
    alternate_emails: list[str]
    phone: str | None
    mobile: str | None
    linkedin_url: str | None
    twitter_url: str | None

    location_country: str | None
    location_state: str | None
    location_city: str | None
    timezone: str | None

    languages: list[str]
    skills: list[str]
    interests: list[str]

    influence_score: int | None
    engagement_score: int | None
    confidence_score: int | None

    relationship_status: RelationshipStatus
    preferred_channel: PreferredChannel | None

    last_contacted_at: datetime | None
    last_replied_at: datetime | None

    notes: str | None
    metadata: dict[str, Any] = Field(validation_alias="metadata_", serialization_alias="metadata")

    status: ContactStatus
    source: ContactSource

    created_by: UUID | None

    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ContactListResponse(BaseModel):
    items: list[ContactResponse]
    total: int
    offset: int
    limit: int
