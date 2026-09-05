from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer, field_validator

from app.models.product import ProductStatus


class ProductCreate(BaseModel):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    website: HttpUrl | None = None
    category: str | None = Field(default=None, max_length=255)
    status: ProductStatus = ProductStatus.DRAFT
    settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "slug", "description", "category")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @field_serializer("website")
    def serialize_website(self, website: HttpUrl | None) -> str | None:
        return str(website) if website is not None else None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    website: HttpUrl | None = None
    category: str | None = Field(default=None, max_length=255)
    status: ProductStatus | None = None
    settings: dict[str, Any] | None = None

    @field_validator("name", "slug", "description", "category")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @field_serializer("website")
    def serialize_website(self, website: HttpUrl | None) -> str | None:
        return str(website) if website is not None else None


class ProductResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    slug: str
    description: str | None
    website: str | None
    category: str | None
    status: ProductStatus
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    offset: int
    limit: int
