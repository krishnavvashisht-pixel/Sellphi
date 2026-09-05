from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.knowledge_document import DocumentType, KnowledgeStatus, SourceType

ContentFormat = Literal["markdown", "html", "plain_text"]


class KnowledgeDocumentCreate(BaseModel):
    product_id: UUID

    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)

    document_type: DocumentType
    content: str = Field(min_length=1)
    content_format: ContentFormat = "markdown"

    source_type: SourceType
    source_url: str | None = Field(default=None, max_length=2048)

    language: str = Field(default="en", max_length=16)

    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # DRAFT lets a caller stage a document without triggering the versioning/
    # archive-previous-version flow; only ACTIVE documents participate in that.
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE

    # Accepted directly for now; in a later sprint this should come from the
    # authenticated request context rather than the request body.
    created_by: UUID | None = None

    @field_validator("title", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class KnowledgeDocumentUpdate(BaseModel):
    """
    `content`, `checksum`, `version`, and `status` are intentionally excluded:
    - content is immutable once created — publish a new document with the same
      title to create a new version (see KnowledgeService.create).
    - status changes only through the dedicated /archive action.
    """

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)

    document_type: DocumentType | None = None
    content_format: ContentFormat | None = None

    source_type: SourceType | None = None
    source_url: str | None = Field(default=None, max_length=2048)

    language: str | None = Field(default=None, max_length=16)

    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("title", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class KnowledgeIndexRequest(BaseModel):
    """Optional body for POST /knowledge/{id}/index, forward-compatible with the
    future embeddings pipeline. Neither field is required this sprint."""

    embedding_id: str | None = Field(default=None, max_length=255)
    chunk_count: int | None = Field(default=None, ge=0)


class KnowledgeDocumentResponse(BaseModel):
    id: UUID
    product_id: UUID

    title: str
    description: str | None

    document_type: DocumentType
    content: str
    content_format: str

    source_type: SourceType
    source_url: str | None

    language: str

    tags: list[str]
    # Reads from the ORM's `metadata_` attribute (see model docstring) but is
    # exposed to API clients as "metadata".
    metadata: dict[str, Any] = Field(validation_alias="metadata_", serialization_alias="metadata")

    version: int
    checksum: str

    status: KnowledgeStatus

    is_indexed: bool
    embedding_id: str | None
    chunk_count: int | None
    last_indexed_at: datetime | None
    indexed_at: datetime | None

    created_by: UUID | None

    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class KnowledgeDocumentListResponse(BaseModel):
    items: list[KnowledgeDocumentResponse]
    total: int
    offset: int
    limit: int
