import hashlib
from typing import Any
from uuid import UUID

from app.core.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
)
from app.events.knowledge_document import (
    KnowledgeArchived,
    KnowledgeCreated,
    KnowledgeDeleted,
    KnowledgeIndexed,
    KnowledgeReindexed,
    KnowledgeUpdated,
)
from app.models.knowledge_document import (
    DocumentType,
    KnowledgeDocument,
    KnowledgeStatus,
    SourceType,
)
from app.repositories.knowledge_document import KnowledgeRepository
from app.repositories.product import ProductRepository
from app.schemas.knowledge_document import KnowledgeDocumentCreate, KnowledgeDocumentUpdate
from app.utils.time import utc_now


# ── Domain exceptions ─────────────────────────────────────────────────────────

class KnowledgeNotFoundError(EntityNotFoundError):
    error_code = "knowledge_document_not_found"


class KnowledgeProductNotFoundError(EntityNotFoundError):
    error_code = "knowledge_product_not_found"


class KnowledgeBusinessRuleError(BusinessRuleViolationError):
    error_code = "knowledge_business_rule_violation"


class KnowledgeDuplicateDocumentError(BusinessRuleViolationError):
    error_code = "knowledge_duplicate_document"


class KnowledgeInvalidTransitionError(BusinessRuleViolationError):
    error_code = "knowledge_invalid_status_transition"


# Source types that only make sense with a URL attached.
_URL_REQUIRED_SOURCE_TYPES = {SourceType.URL_IMPORT, SourceType.API_SYNC, SourceType.CRM_SYNC}


def _compute_checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ── Service ───────────────────────────────────────────────────────────────────

class KnowledgeService:
    def __init__(
        self,
        knowledge_repository: KnowledgeRepository,
        product_repository: ProductRepository,
    ) -> None:
        self._knowledge_repository = knowledge_repository
        self._product_repository = product_repository

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create(self, payload: KnowledgeDocumentCreate) -> KnowledgeDocument:
        await self._ensure_product_exists(payload.product_id)
        self._validate_document_type(payload.document_type)
        self._validate_source(payload.source_type, payload.source_url)

        checksum = _compute_checksum(payload.content)
        await self._ensure_not_duplicate(payload.product_id, checksum)

        existing_active: KnowledgeDocument | None = None
        if payload.status == KnowledgeStatus.ACTIVE:
            existing_active = await self._knowledge_repository.get_active_by_title(
                payload.title, payload.product_id
            )

        latest = await self._knowledge_repository.get_latest_version(payload.title, payload.product_id)
        version = (latest.version + 1) if latest is not None else 1

        document = KnowledgeDocument(
            product_id=payload.product_id,
            title=payload.title,
            description=payload.description,
            document_type=payload.document_type,
            content=payload.content,
            content_format=payload.content_format,
            source_type=payload.source_type,
            source_url=payload.source_url,
            language=payload.language,
            tags=payload.tags,
            metadata_=payload.metadata,
            version=version,
            checksum=checksum,
            status=payload.status,
            is_indexed=False,
            created_by=payload.created_by,
        )

        try:
            created = await self._knowledge_repository.create(document)
            if existing_active is not None:
                existing_active.status = KnowledgeStatus.ARCHIVED
                await self._knowledge_repository.update(existing_active)
            await self._knowledge_repository.commit()
        except Exception:
            await self._knowledge_repository.rollback()
            raise

        _emit(KnowledgeCreated.create(
            document_id=created.id, product_id=created.product_id, title=created.title, version=created.version,
        ))
        if existing_active is not None:
            _emit(KnowledgeArchived.create(
                document_id=existing_active.id,
                product_id=existing_active.product_id,
                reason="superseded_by_new_version",
            ))

        return created

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        tags: list[str] | None = None,
        document_type: DocumentType | None = None,
        source_type: SourceType | None = None,
        status: KnowledgeStatus | None = None,
    ) -> tuple[list[KnowledgeDocument], int]:
        await self._ensure_product_exists(product_id)
        return await self._knowledge_repository.list(
            product_id=product_id,
            offset=offset,
            limit=limit,
            search=search,
            tags=tags,
            document_type=document_type,
            source_type=source_type,
            status=status,
        )

    async def get(self, document_id: UUID, product_id: UUID | None = None) -> KnowledgeDocument:
        document = await self._knowledge_repository.get_by_id(document_id, product_id=product_id)
        if document is None:
            raise KnowledgeNotFoundError("Knowledge document not found")
        return document

    async def get_versions(self, title: str, product_id: UUID) -> list[KnowledgeDocument]:
        await self._ensure_product_exists(product_id)
        return await self._knowledge_repository.get_versions(title, product_id)

    async def update(self, document_id: UUID, payload: KnowledgeDocumentUpdate) -> KnowledgeDocument:
        document = await self.get(document_id)
        if document.status == KnowledgeStatus.ARCHIVED:
            raise KnowledgeBusinessRuleError("Cannot update an archived document")

        updates = payload.model_dump(exclude_unset=True)

        new_document_type = updates.get("document_type", document.document_type)
        if "document_type" in updates:
            self._validate_document_type(new_document_type)

        if "source_type" in updates or "source_url" in updates:
            new_source_type = updates.get("source_type", document.source_type)
            new_source_url = updates.get("source_url", document.source_url)
            self._validate_source(new_source_type, new_source_url)

        _SIMPLE_FIELDS = {
            "title", "description", "document_type", "content_format",
            "source_type", "source_url", "language", "tags",
        }
        for field in _SIMPLE_FIELDS:
            if field in updates:
                setattr(document, field, updates[field])

        if "metadata" in updates:
            document.metadata_ = updates["metadata"]

        try:
            updated = await self._knowledge_repository.update(document)
            await self._knowledge_repository.commit()
        except Exception:
            await self._knowledge_repository.rollback()
            raise

        _emit(KnowledgeUpdated.create(
            document_id=updated.id, product_id=updated.product_id, updated_fields=list(updates.keys()),
        ))
        return updated

    # ── Status / lifecycle actions ──────────────────────────────────────────

    async def archive(self, document_id: UUID) -> KnowledgeDocument:
        document = await self.get(document_id)
        if document.status == KnowledgeStatus.ARCHIVED:
            raise KnowledgeInvalidTransitionError("Document is already archived")

        document.status = KnowledgeStatus.ARCHIVED
        await self._persist(document)

        _emit(KnowledgeArchived.create(document_id=document.id, product_id=document.product_id, reason="manual"))
        return document

    async def mark_indexed(
        self, document_id: UUID, *, embedding_id: str | None = None, chunk_count: int | None = None
    ) -> KnowledgeDocument:
        document = await self.get(document_id)
        was_indexed = document.is_indexed
        now = utc_now()

        document.is_indexed = True
        if embedding_id is not None:
            document.embedding_id = embedding_id
        if chunk_count is not None:
            document.chunk_count = chunk_count
        if document.indexed_at is None:
            document.indexed_at = now
        document.last_indexed_at = now

        await self._persist(document)

        if was_indexed:
            _emit(KnowledgeReindexed.create(document_id=document.id, product_id=document.product_id))
        else:
            _emit(KnowledgeIndexed.create(document_id=document.id, product_id=document.product_id))
        return document

    async def mark_unindexed(self, document_id: UUID) -> KnowledgeDocument:
        """
        Service-only capability (no REST route in this sprint's endpoint list).
        Useful for future workflows that need to invalidate a stale embedding
        without deleting the document itself.
        """
        document = await self.get(document_id)
        document.is_indexed = False
        document.embedding_id = None
        document.chunk_count = None
        await self._persist(document)
        return document

    async def delete(self, document_id: UUID) -> None:
        document = await self.get(document_id)
        document.deleted_at = utc_now()

        try:
            await self._knowledge_repository.soft_delete(document)
            await self._knowledge_repository.commit()
        except Exception:
            await self._knowledge_repository.rollback()
            raise

        _emit(KnowledgeDeleted.create(document_id=document.id, product_id=document.product_id))

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _persist(self, document: KnowledgeDocument) -> KnowledgeDocument:
        try:
            updated = await self._knowledge_repository.update(document)
            await self._knowledge_repository.commit()
            return updated
        except Exception:
            await self._knowledge_repository.rollback()
            raise

    async def _ensure_product_exists(self, product_id: UUID) -> None:
        product = await self._product_repository.get_by_id(product_id)
        if product is None:
            raise KnowledgeProductNotFoundError("Product not found")

    async def _ensure_not_duplicate(self, product_id: UUID, checksum: str) -> None:
        existing = await self._knowledge_repository.get_by_checksum(checksum, product_id)
        if existing is not None:
            raise KnowledgeDuplicateDocumentError(
                f"A document with identical content already exists in this product (id={existing.id})"
            )

    def _validate_document_type(self, document_type: DocumentType) -> None:
        if not isinstance(document_type, DocumentType):
            raise KnowledgeBusinessRuleError(f"Invalid document_type: {document_type!r}")

    def _validate_source(self, source_type: SourceType, source_url: str | None) -> None:
        if not isinstance(source_type, SourceType):
            raise KnowledgeBusinessRuleError(f"Invalid source_type: {source_type!r}")
        if source_type in _URL_REQUIRED_SOURCE_TYPES and not source_url:
            raise KnowledgeBusinessRuleError(
                f"source_url is required when source_type is '{source_type.value}'"
            )
        if source_type == SourceType.MANUAL_UPLOAD and source_url:
            raise KnowledgeBusinessRuleError(
                "source_url must not be set when source_type is 'manual_upload'"
            )


def _emit(event: object) -> None:
    """
    Fire-and-forget event emission.
    In production wire up an EventBus here (Redis Streams, Kafka, etc.).
    """
    # TODO: inject EventBus and call await event_bus.publish(event)
    pass
