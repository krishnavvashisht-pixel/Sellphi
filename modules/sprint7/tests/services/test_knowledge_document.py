from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.models.knowledge_document import (
    DocumentType,
    KnowledgeDocument,
    KnowledgeStatus,
    SourceType,
)
from app.models.product import Product, ProductStatus
from app.schemas.knowledge_document import KnowledgeDocumentCreate, KnowledgeDocumentUpdate
from app.services.knowledge_document import (
    KnowledgeBusinessRuleError,
    KnowledgeDuplicateDocumentError,
    KnowledgeInvalidTransitionError,
    KnowledgeNotFoundError,
    KnowledgeProductNotFoundError,
    KnowledgeService,
)


# ── Fake repositories ─────────────────────────────────────────────────────────

class FakeKnowledgeRepository:
    def __init__(self, documents: list[KnowledgeDocument] | None = None) -> None:
        self.documents = documents or []
        self.commits = 0
        self.rollbacks = 0

    async def create(self, document: KnowledgeDocument) -> KnowledgeDocument:
        self._hydrate(document)
        self.documents.append(document)
        return document

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
        filtered = [
            d for d in self.documents
            if d.product_id == product_id and d.deleted_at is None
        ]
        if status is not None:
            filtered = [d for d in filtered if d.status == status]
        if document_type is not None:
            filtered = [d for d in filtered if d.document_type == document_type]
        if source_type is not None:
            filtered = [d for d in filtered if d.source_type == source_type]
        if search:
            q = search.lower()
            filtered = [d for d in filtered if q in d.title.lower()]
        if tags:
            tag_set = set(tags)
            filtered = [d for d in filtered if tag_set & set(d.tags)]
        return filtered[offset: offset + limit], len(filtered)

    async def get_by_id(self, document_id: UUID, product_id: UUID | None = None) -> KnowledgeDocument | None:
        return next(
            (
                d for d in self.documents
                if d.id == document_id
                and d.deleted_at is None
                and (product_id is None or d.product_id == product_id)
            ),
            None,
        )

    async def get_by_checksum(self, checksum: str, product_id: UUID) -> KnowledgeDocument | None:
        return next(
            (
                d for d in self.documents
                if d.product_id == product_id
                and d.checksum == checksum
                and d.deleted_at is None
                and d.status != KnowledgeStatus.ARCHIVED
            ),
            None,
        )

    async def get_active_by_title(self, title: str, product_id: UUID) -> KnowledgeDocument | None:
        return next(
            (
                d for d in self.documents
                if d.product_id == product_id
                and d.title == title
                and d.status == KnowledgeStatus.ACTIVE
                and d.deleted_at is None
            ),
            None,
        )

    async def get_latest_version(self, title: str, product_id: UUID) -> KnowledgeDocument | None:
        candidates = [
            d for d in self.documents
            if d.product_id == product_id and d.title == title and d.deleted_at is None
        ]
        return max(candidates, key=lambda d: d.version) if candidates else None

    async def get_versions(self, title: str, product_id: UUID) -> list[KnowledgeDocument]:
        candidates = [
            d for d in self.documents
            if d.product_id == product_id and d.title == title and d.deleted_at is None
        ]
        return sorted(candidates, key=lambda d: d.version, reverse=True)

    async def update(self, document: KnowledgeDocument) -> KnowledgeDocument:
        document.updated_at = datetime.now(UTC)
        return document

    async def soft_delete(self, document: KnowledgeDocument) -> KnowledgeDocument:
        return document

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    def _hydrate(self, document: KnowledgeDocument) -> None:
        now = datetime.now(UTC)
        document.id = uuid4()
        document.created_at = now
        document.updated_at = now
        document.deleted_at = None
        document.is_deleted = False


class FakeProductRepository:
    def __init__(self, product_ids: set[UUID]) -> None:
        self.product_ids = product_ids

    async def get_by_id(self, product_id: UUID, workspace_id: UUID | None = None) -> Product | None:
        if product_id not in self.product_ids:
            return None
        now = datetime.now(UTC)
        product = Product(
            workspace_id=uuid4(),
            name="Test Product",
            slug="test-product",
            status=ProductStatus.ACTIVE,
            settings={},
        )
        product.id = product_id
        product.created_at = now
        product.updated_at = now
        product.deleted_at = None
        product.is_deleted = False
        return product


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def product_id() -> UUID:
    return uuid4()


@pytest.fixture
def other_product_id() -> UUID:
    return uuid4()


@pytest.fixture
def knowledge_repo() -> FakeKnowledgeRepository:
    return FakeKnowledgeRepository()


@pytest.fixture
def service(
    knowledge_repo: FakeKnowledgeRepository, product_id: UUID, other_product_id: UUID
) -> KnowledgeService:
    product_repo = FakeProductRepository({product_id, other_product_id})
    return KnowledgeService(knowledge_repository=knowledge_repo, product_repository=product_repo)


def _create_payload(product_id: UUID, **overrides: object) -> KnowledgeDocumentCreate:
    return KnowledgeDocumentCreate(
        product_id=product_id,
        title=overrides.get("title", "Pricing FAQ"),  # type: ignore[arg-type]
        description=overrides.get("description"),  # type: ignore[arg-type]
        document_type=overrides.get("document_type", DocumentType.FAQ),  # type: ignore[arg-type]
        content=overrides.get("content", "Our pricing starts at $99/month."),  # type: ignore[arg-type]
        content_format=overrides.get("content_format", "markdown"),  # type: ignore[arg-type]
        source_type=overrides.get("source_type", SourceType.MANUAL_UPLOAD),  # type: ignore[arg-type]
        source_url=overrides.get("source_url"),  # type: ignore[arg-type]
        language=overrides.get("language", "en"),  # type: ignore[arg-type]
        tags=overrides.get("tags", []),  # type: ignore[arg-type]
        metadata=overrides.get("metadata", {}),  # type: ignore[arg-type]
        status=overrides.get("status", KnowledgeStatus.ACTIVE),  # type: ignore[arg-type]
        created_by=overrides.get("created_by"),  # type: ignore[arg-type]
    )


# ── CRUD tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_document(
    service: KnowledgeService, knowledge_repo: FakeKnowledgeRepository, product_id: UUID
) -> None:
    document = await service.create(_create_payload(product_id, title="Enterprise Pricing"))

    assert document.id is not None
    assert document.title == "Enterprise Pricing"
    assert document.product_id == product_id
    assert document.version == 1
    assert document.status == KnowledgeStatus.ACTIVE
    assert document.is_indexed is False
    assert len(document.checksum) == 64  # sha256 hex digest
    assert knowledge_repo.commits == 1


@pytest.mark.asyncio
async def test_create_document_product_not_found(service: KnowledgeService) -> None:
    with pytest.raises(KnowledgeProductNotFoundError):
        await service.create(_create_payload(uuid4()))


@pytest.mark.asyncio
async def test_get_document(service: KnowledgeService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    fetched = await service.get(created.id)
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_document_not_found(service: KnowledgeService) -> None:
    with pytest.raises(KnowledgeNotFoundError):
        await service.get(uuid4())


@pytest.mark.asyncio
async def test_update_document_metadata(service: KnowledgeService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    updated = await service.update(created.id, KnowledgeDocumentUpdate(title="Renamed FAQ"))
    assert updated.title == "Renamed FAQ"


@pytest.mark.asyncio
async def test_update_metadata_field(service: KnowledgeService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    updated = await service.update(
        created.id, KnowledgeDocumentUpdate(metadata={"reviewed_by": "sales-ops"})
    )
    assert updated.metadata_ == {"reviewed_by": "sales-ops"}


@pytest.mark.asyncio
async def test_cannot_update_archived_document(service: KnowledgeService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.archive(created.id)

    with pytest.raises(KnowledgeBusinessRuleError, match="archived"):
        await service.update(created.id, KnowledgeDocumentUpdate(title="New Title"))


# ── Source-type validation ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_url_import_requires_source_url(service: KnowledgeService, product_id: UUID) -> None:
    with pytest.raises(KnowledgeBusinessRuleError, match="source_url is required"):
        await service.create(
            _create_payload(product_id, source_type=SourceType.URL_IMPORT, source_url=None)
        )


@pytest.mark.asyncio
async def test_manual_upload_rejects_source_url(service: KnowledgeService, product_id: UUID) -> None:
    with pytest.raises(KnowledgeBusinessRuleError, match="must not be set"):
        await service.create(
            _create_payload(
                product_id, source_type=SourceType.MANUAL_UPLOAD, source_url="https://example.com"
            )
        )


@pytest.mark.asyncio
async def test_url_import_with_source_url_accepted(service: KnowledgeService, product_id: UUID) -> None:
    document = await service.create(
        _create_payload(
            product_id, source_type=SourceType.URL_IMPORT, source_url="https://example.com/pricing"
        )
    )
    assert document.source_url == "https://example.com/pricing"


# ── Duplicate detection ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_content_rejected(service: KnowledgeService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, title="Doc A", content="Identical content"))

    with pytest.raises(KnowledgeDuplicateDocumentError):
        await service.create(_create_payload(product_id, title="Doc B", content="Identical content"))


@pytest.mark.asyncio
async def test_same_content_allowed_across_products(
    service: KnowledgeService, product_id: UUID, other_product_id: UUID
) -> None:
    a = await service.create(_create_payload(product_id, content="Shared content"))
    b = await service.create(_create_payload(other_product_id, content="Shared content"))
    assert a.id != b.id


@pytest.mark.asyncio
async def test_different_content_same_title_not_flagged_as_duplicate(
    service: KnowledgeService, product_id: UUID
) -> None:
    await service.create(_create_payload(product_id, title="Pricing FAQ", content="v1 content"))
    # Different content under the same title is a new *version*, not a duplicate.
    updated = await service.create(_create_payload(product_id, title="Pricing FAQ", content="v2 content"))
    assert updated.version == 2


# ── Versioning ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_new_version_increments_and_archives_previous(
    service: KnowledgeService, knowledge_repo: FakeKnowledgeRepository, product_id: UUID
) -> None:
    v1 = await service.create(_create_payload(product_id, title="Onboarding Guide", content="v1"))
    assert v1.version == 1
    assert v1.status == KnowledgeStatus.ACTIVE

    v2 = await service.create(_create_payload(product_id, title="Onboarding Guide", content="v2"))
    assert v2.version == 2
    assert v2.status == KnowledgeStatus.ACTIVE

    v1_refetched = await knowledge_repo.get_by_id(v1.id)
    assert v1_refetched is not None
    assert v1_refetched.status == KnowledgeStatus.ARCHIVED


@pytest.mark.asyncio
async def test_draft_version_does_not_archive_active(
    service: KnowledgeService, knowledge_repo: FakeKnowledgeRepository, product_id: UUID
) -> None:
    active = await service.create(_create_payload(product_id, title="Playbook", content="active content"))
    draft = await service.create(
        _create_payload(
            product_id, title="Playbook", content="draft content", status=KnowledgeStatus.DRAFT
        )
    )
    assert draft.status == KnowledgeStatus.DRAFT

    active_refetched = await knowledge_repo.get_by_id(active.id)
    assert active_refetched is not None
    assert active_refetched.status == KnowledgeStatus.ACTIVE  # untouched


@pytest.mark.asyncio
async def test_get_versions_returns_full_history(service: KnowledgeService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, title="Sales Script", content="v1"))
    await service.create(_create_payload(product_id, title="Sales Script", content="v2"))
    await service.create(_create_payload(product_id, title="Sales Script", content="v3"))

    versions = await service.get_versions("Sales Script", product_id)
    assert [v.version for v in versions] == [3, 2, 1]


# ── Archive action ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_archive_document(service: KnowledgeService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    archived = await service.archive(created.id)
    assert archived.status == KnowledgeStatus.ARCHIVED


@pytest.mark.asyncio
async def test_cannot_archive_already_archived_document(service: KnowledgeService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.archive(created.id)

    with pytest.raises(KnowledgeInvalidTransitionError):
        await service.archive(created.id)


# ── Index status ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_indexed_first_time(service: KnowledgeService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    assert created.is_indexed is False
    assert created.indexed_at is None

    indexed = await service.mark_indexed(created.id, embedding_id="emb-123", chunk_count=5)
    assert indexed.is_indexed is True
    assert indexed.embedding_id == "emb-123"
    assert indexed.chunk_count == 5
    assert indexed.indexed_at is not None
    assert indexed.last_indexed_at is not None


@pytest.mark.asyncio
async def test_mark_indexed_twice_preserves_original_indexed_at(
    service: KnowledgeService, product_id: UUID
) -> None:
    created = await service.create(_create_payload(product_id))
    first = await service.mark_indexed(created.id, embedding_id="emb-1")
    first_indexed_at = first.indexed_at

    second = await service.mark_indexed(created.id, embedding_id="emb-2")
    assert second.indexed_at == first_indexed_at  # unchanged
    assert second.embedding_id == "emb-2"  # updated


@pytest.mark.asyncio
async def test_mark_unindexed(service: KnowledgeService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.mark_indexed(created.id, embedding_id="emb-1", chunk_count=3)

    unindexed = await service.mark_unindexed(created.id)
    assert unindexed.is_indexed is False
    assert unindexed.embedding_id is None
    assert unindexed.chunk_count is None


# ── Soft delete ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(service: KnowledgeService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    assert created.deleted_at is None

    await service.delete(created.id)
    assert created.deleted_at is not None


@pytest.mark.asyncio
async def test_soft_deleted_document_excluded_from_list(service: KnowledgeService, product_id: UUID) -> None:
    keep = await service.create(_create_payload(product_id, title="Keep"))
    delete_me = await service.create(_create_payload(product_id, title="Delete", content="other content"))
    await service.delete(delete_me.id)

    documents, total = await service.list(product_id=product_id)
    assert total == 1
    assert documents[0].id == keep.id


@pytest.mark.asyncio
async def test_soft_deleted_document_not_found_by_id(service: KnowledgeService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.delete(created.id)

    with pytest.raises(KnowledgeNotFoundError):
        await service.get(created.id)


# ── Product isolation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_document_product_isolation(
    service: KnowledgeService, product_id: UUID, other_product_id: UUID
) -> None:
    await service.create(_create_payload(product_id, title="Product A Doc"))
    await service.create(_create_payload(other_product_id, title="Product B Doc", content="different"))

    docs_a, total_a = await service.list(product_id=product_id)
    docs_b, total_b = await service.list(product_id=other_product_id)

    assert total_a == 1
    assert total_b == 1
    assert docs_a[0].title == "Product A Doc"
    assert docs_b[0].title == "Product B Doc"


# ── Search & filters ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_by_title(service: KnowledgeService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, title="Enterprise Pricing", content="c1"))
    await service.create(_create_payload(product_id, title="SMB Pricing", content="c2"))

    results, total = await service.list(product_id=product_id, search="Enterprise")
    assert total == 1
    assert results[0].title == "Enterprise Pricing"


@pytest.mark.asyncio
async def test_search_by_tags(service: KnowledgeService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, title="Doc A", content="c1", tags=["pricing", "faq"]))
    await service.create(_create_payload(product_id, title="Doc B", content="c2", tags=["onboarding"]))

    results, total = await service.list(product_id=product_id, tags=["pricing"])
    assert total == 1
    assert results[0].title == "Doc A"


@pytest.mark.asyncio
async def test_filter_by_document_type(service: KnowledgeService, product_id: UUID) -> None:
    await service.create(
        _create_payload(product_id, title="FAQ Doc", content="c1", document_type=DocumentType.FAQ)
    )
    await service.create(
        _create_payload(
            product_id, title="Pricing Doc", content="c2", document_type=DocumentType.PRICING
        )
    )

    results, total = await service.list(product_id=product_id, document_type=DocumentType.PRICING)
    assert total == 1
    assert results[0].title == "Pricing Doc"


# ── Pagination ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_pagination(service: KnowledgeService, product_id: UUID) -> None:
    for i in range(5):
        await service.create(_create_payload(product_id, title=f"Doc {i}", content=f"content {i}"))

    page1, total = await service.list(product_id=product_id, offset=0, limit=2)
    page2, _ = await service.list(product_id=product_id, offset=2, limit=2)
    page3, _ = await service.list(product_id=product_id, offset=4, limit=2)

    assert total == 5
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1
