from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.api.v1.knowledge.routes import get_knowledge_service
from app.main import app
from app.schemas.knowledge_document import KnowledgeDocumentCreate, KnowledgeDocumentUpdate
from app.services.knowledge_document import (
    KnowledgeBusinessRuleError,
    KnowledgeDuplicateDocumentError,
    KnowledgeInvalidTransitionError,
    KnowledgeNotFoundError,
    KnowledgeProductNotFoundError,
)


# ── Fake service ──────────────────────────────────────────────────────────────

class FakeKnowledgeService:
    def __init__(self) -> None:
        self.product_id = uuid4()
        self.document_id = uuid4()
        self.deleted_ids: list[UUID] = []

    async def create(self, payload: KnowledgeDocumentCreate) -> object:
        return self._document(
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
            metadata=payload.metadata,
            status=payload.status,
            created_by=payload.created_by,
        )

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        tags: list[str] | None = None,
        document_type: object | None = None,
        source_type: object | None = None,
        status: object | None = None,
    ) -> tuple[list[object], int]:
        return [self._document(product_id=product_id)], 1

    async def get(self, document_id: UUID, product_id: UUID | None = None) -> object:
        return self._document(document_id=document_id)

    async def update(self, document_id: UUID, payload: KnowledgeDocumentUpdate) -> object:
        return self._document(document_id=document_id, title=payload.title or "Updated Document")

    async def delete(self, document_id: UUID) -> None:
        self.deleted_ids.append(document_id)

    async def archive(self, document_id: UUID) -> object:
        return self._document(document_id=document_id, status="archived")

    async def mark_indexed(
        self, document_id: UUID, *, embedding_id: str | None = None, chunk_count: int | None = None
    ) -> object:
        return self._document(
            document_id=document_id,
            is_indexed=True,
            embedding_id=embedding_id,
            chunk_count=chunk_count,
            indexed_at=datetime.now(UTC),
            last_indexed_at=datetime.now(UTC),
        )

    def _document(
        self,
        *,
        document_id: UUID | None = None,
        product_id: UUID | None = None,
        title: str = "Pricing FAQ",
        description: str | None = None,
        document_type: object = "faq",
        content: str = "Our pricing starts at $99/month.",
        content_format: str = "markdown",
        source_type: object = "manual_upload",
        source_url: str | None = None,
        language: str = "en",
        tags: list[str] | None = None,
        metadata: dict | None = None,
        version: int = 1,
        checksum: str = "a" * 64,
        status: object = "active",
        is_indexed: bool = False,
        embedding_id: str | None = None,
        chunk_count: int | None = None,
        last_indexed_at: object = None,
        indexed_at: object = None,
        created_by: UUID | None = None,
    ) -> object:
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=document_id or self.document_id,
            product_id=product_id or self.product_id,
            title=title,
            description=description,
            document_type=document_type,
            content=content,
            content_format=content_format,
            source_type=source_type,
            source_url=source_url,
            language=language,
            tags=tags or [],
            metadata_=metadata or {},
            version=version,
            checksum=checksum,
            status=status,
            is_indexed=is_indexed,
            embedding_id=embedding_id,
            chunk_count=chunk_count,
            last_indexed_at=last_indexed_at,
            indexed_at=indexed_at,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )


@pytest.fixture
def knowledge_service() -> FakeKnowledgeService:
    service = FakeKnowledgeService()
    app.dependency_overrides[get_knowledge_service] = lambda: service
    return service


# ── POST /api/v1/knowledge ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_document(client: AsyncClient, knowledge_service: FakeKnowledgeService) -> None:
    response = await client.post(
        "/api/v1/knowledge",
        json={
            "product_id": str(knowledge_service.product_id),
            "title": "Pricing FAQ",
            "document_type": "faq",
            "content": "Our pricing starts at $99/month.",
            "source_type": "manual_upload",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Pricing FAQ"
    assert data["product_id"] == str(knowledge_service.product_id)
    assert data["version"] == 1
    assert "metadata" in data


@pytest.mark.asyncio
async def test_create_document_missing_content_rejected(
    client: AsyncClient, knowledge_service: FakeKnowledgeService
) -> None:
    response = await client.post(
        "/api/v1/knowledge",
        json={
            "product_id": str(knowledge_service.product_id),
            "title": "Empty Doc",
            "document_type": "faq",
            "content": "",
            "source_type": "manual_upload",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_document_product_not_found(
    client: AsyncClient, knowledge_service: FakeKnowledgeService
) -> None:
    async def raise_not_found(payload: KnowledgeDocumentCreate) -> None:
        raise KnowledgeProductNotFoundError("Product not found")

    knowledge_service.create = raise_not_found  # type: ignore[method-assign]

    response = await client.post(
        "/api/v1/knowledge",
        json={
            "product_id": str(uuid4()),
            "title": "Doc",
            "document_type": "faq",
            "content": "content",
            "source_type": "manual_upload",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_document_duplicate_rejected(
    client: AsyncClient, knowledge_service: FakeKnowledgeService
) -> None:
    async def raise_duplicate(payload: KnowledgeDocumentCreate) -> None:
        raise KnowledgeDuplicateDocumentError("A document with identical content already exists")

    knowledge_service.create = raise_duplicate  # type: ignore[method-assign]

    response = await client.post(
        "/api/v1/knowledge",
        json={
            "product_id": str(knowledge_service.product_id),
            "title": "Doc",
            "document_type": "faq",
            "content": "content",
            "source_type": "manual_upload",
        },
    )
    assert response.status_code == 422


# ── GET /api/v1/knowledge ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, knowledge_service: FakeKnowledgeService) -> None:
    response = await client.get(
        "/api/v1/knowledge",
        params={"product_id": str(knowledge_service.product_id)},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_documents_missing_product_id(
    client: AsyncClient, knowledge_service: FakeKnowledgeService
) -> None:
    response = await client.get("/api/v1/knowledge")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_documents_with_tags_filter(
    client: AsyncClient, knowledge_service: FakeKnowledgeService
) -> None:
    response = await client.get(
        "/api/v1/knowledge",
        params={"product_id": str(knowledge_service.product_id), "tags": ["pricing", "faq"]},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_documents_with_status_filter(
    client: AsyncClient, knowledge_service: FakeKnowledgeService
) -> None:
    response = await client.get(
        "/api/v1/knowledge",
        params={"product_id": str(knowledge_service.product_id), "status": "active"},
    )
    assert response.status_code == 200


# ── GET /api/v1/knowledge/{id} ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_document(client: AsyncClient, knowledge_service: FakeKnowledgeService) -> None:
    response = await client.get(f"/api/v1/knowledge/{knowledge_service.document_id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(knowledge_service.document_id)


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient, knowledge_service: FakeKnowledgeService) -> None:
    async def raise_not_found(document_id: UUID, product_id: UUID | None = None) -> None:
        raise KnowledgeNotFoundError("Knowledge document not found")

    knowledge_service.get = raise_not_found  # type: ignore[method-assign]

    response = await client.get(f"/api/v1/knowledge/{uuid4()}")
    assert response.status_code == 404


# ── PATCH /api/v1/knowledge/{id} ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_document(client: AsyncClient, knowledge_service: FakeKnowledgeService) -> None:
    response = await client.patch(
        f"/api/v1/knowledge/{knowledge_service.document_id}",
        json={"title": "Updated Document"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Document"


@pytest.mark.asyncio
async def test_update_archived_document_rejected(
    client: AsyncClient, knowledge_service: FakeKnowledgeService
) -> None:
    async def raise_rule_error(document_id: UUID, payload: KnowledgeDocumentUpdate) -> None:
        raise KnowledgeBusinessRuleError("Cannot update an archived document")

    knowledge_service.update = raise_rule_error  # type: ignore[method-assign]

    response = await client.patch(
        f"/api/v1/knowledge/{knowledge_service.document_id}",
        json={"title": "New Title"},
    )
    assert response.status_code == 422


# ── DELETE /api/v1/knowledge/{id} ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, knowledge_service: FakeKnowledgeService) -> None:
    response = await client.delete(f"/api/v1/knowledge/{knowledge_service.document_id}")
    assert response.status_code == 204
    assert knowledge_service.document_id in knowledge_service.deleted_ids


# ── POST /api/v1/knowledge/{id}/index ────────────────────────────────────────

@pytest.mark.asyncio
async def test_index_document(client: AsyncClient, knowledge_service: FakeKnowledgeService) -> None:
    response = await client.post(
        f"/api/v1/knowledge/{knowledge_service.document_id}/index",
        json={"embedding_id": "emb-123", "chunk_count": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_indexed"] is True
    assert data["embedding_id"] == "emb-123"
    assert data["chunk_count"] == 5


@pytest.mark.asyncio
async def test_index_document_without_body(client: AsyncClient, knowledge_service: FakeKnowledgeService) -> None:
    response = await client.post(f"/api/v1/knowledge/{knowledge_service.document_id}/index")
    assert response.status_code == 200
    assert response.json()["is_indexed"] is True


# ── POST /api/v1/knowledge/{id}/archive ──────────────────────────────────────

@pytest.mark.asyncio
async def test_archive_document(client: AsyncClient, knowledge_service: FakeKnowledgeService) -> None:
    response = await client.post(f"/api/v1/knowledge/{knowledge_service.document_id}/archive")
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_archive_already_archived_document_rejected(
    client: AsyncClient, knowledge_service: FakeKnowledgeService
) -> None:
    async def raise_transition_error(document_id: UUID) -> None:
        raise KnowledgeInvalidTransitionError("Document is already archived")

    knowledge_service.archive = raise_transition_error  # type: ignore[method-assign]

    response = await client.post(f"/api/v1/knowledge/{knowledge_service.document_id}/archive")
    assert response.status_code == 422
