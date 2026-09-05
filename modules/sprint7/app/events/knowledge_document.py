from dataclasses import dataclass
from uuid import UUID

from app.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class KnowledgeCreated(DomainEvent):
    """Emitted when a new document (or a new version of one) is created."""

    @classmethod
    def create(
        cls, document_id: UUID, product_id: UUID, title: str, version: int
    ) -> "KnowledgeCreated":
        return cls(
            payload={
                "document_id": str(document_id),
                "product_id": str(product_id),
                "title": title,
                "version": version,
            }
        )


@dataclass(frozen=True, slots=True)
class KnowledgeUpdated(DomainEvent):
    """Emitted when a document's metadata (not content) is updated."""

    @classmethod
    def create(cls, document_id: UUID, product_id: UUID, updated_fields: list[str]) -> "KnowledgeUpdated":
        return cls(
            payload={
                "document_id": str(document_id),
                "product_id": str(product_id),
                "updated_fields": updated_fields,
            }
        )


@dataclass(frozen=True, slots=True)
class KnowledgeArchived(DomainEvent):
    """Emitted when a document is archived, either manually or because a newer
    version superseded it."""

    @classmethod
    def create(cls, document_id: UUID, product_id: UUID, reason: str) -> "KnowledgeArchived":
        return cls(
            payload={
                "document_id": str(document_id),
                "product_id": str(product_id),
                "reason": reason,  # "manual" | "superseded_by_new_version"
            }
        )


@dataclass(frozen=True, slots=True)
class KnowledgeDeleted(DomainEvent):
    """Emitted when a document is soft-deleted."""

    @classmethod
    def create(cls, document_id: UUID, product_id: UUID) -> "KnowledgeDeleted":
        return cls(
            payload={
                "document_id": str(document_id),
                "product_id": str(product_id),
            }
        )


@dataclass(frozen=True, slots=True)
class KnowledgeIndexed(DomainEvent):
    """Emitted the first time a document is marked indexed."""

    @classmethod
    def create(cls, document_id: UUID, product_id: UUID) -> "KnowledgeIndexed":
        return cls(
            payload={
                "document_id": str(document_id),
                "product_id": str(product_id),
            }
        )


@dataclass(frozen=True, slots=True)
class KnowledgeReindexed(DomainEvent):
    """Emitted on subsequent indexing of an already-indexed document."""

    @classmethod
    def create(cls, document_id: UUID, product_id: UUID) -> "KnowledgeReindexed":
        return cls(
            payload={
                "document_id": str(document_id),
                "product_id": str(product_id),
            }
        )
