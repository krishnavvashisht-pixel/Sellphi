from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import DbSessionDep
from app.models.knowledge_document import DocumentType, KnowledgeStatus, SourceType
from app.repositories.knowledge_document import KnowledgeRepository
from app.repositories.product import ProductRepository
from app.schemas.knowledge_document import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
    KnowledgeDocumentUpdate,
    KnowledgeIndexRequest,
)
from app.services.knowledge_document import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_knowledge_service(db_session: DbSessionDep) -> KnowledgeService:
    return KnowledgeService(
        knowledge_repository=KnowledgeRepository(db_session),
        product_repository=ProductRepository(db_session),
    )


KnowledgeServiceDep = Annotated[KnowledgeService, Depends(get_knowledge_service)]


@router.post(
    "",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_document(
    payload: KnowledgeDocumentCreate,
    service: KnowledgeServiceDep,
) -> KnowledgeDocumentResponse:
    document = await service.create(payload)
    return KnowledgeDocumentResponse.model_validate(document)


@router.get("", response_model=KnowledgeDocumentListResponse)
async def list_knowledge_documents(
    service: KnowledgeServiceDep,
    product_id: Annotated[UUID, Query()],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    tags: Annotated[list[str] | None, Query()] = None,
    document_type: Annotated[DocumentType | None, Query()] = None,
    source_type: Annotated[SourceType | None, Query()] = None,
    status_filter: Annotated[KnowledgeStatus | None, Query(alias="status")] = None,
) -> KnowledgeDocumentListResponse:
    documents, total = await service.list(
        product_id=product_id,
        offset=offset,
        limit=limit,
        search=search,
        tags=tags,
        document_type=document_type,
        source_type=source_type,
        status=status_filter,
    )
    return KnowledgeDocumentListResponse(
        items=[KnowledgeDocumentResponse.model_validate(document) for document in documents],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_knowledge_document(
    document_id: UUID,
    service: KnowledgeServiceDep,
) -> KnowledgeDocumentResponse:
    document = await service.get(document_id)
    return KnowledgeDocumentResponse.model_validate(document)


@router.patch("/{document_id}", response_model=KnowledgeDocumentResponse)
async def update_knowledge_document(
    document_id: UUID,
    payload: KnowledgeDocumentUpdate,
    service: KnowledgeServiceDep,
) -> KnowledgeDocumentResponse:
    document = await service.update(document_id, payload)
    return KnowledgeDocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_document(
    document_id: UUID,
    service: KnowledgeServiceDep,
) -> Response:
    await service.delete(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Lifecycle actions ──────────────────────────────────────────────────────────

@router.post("/{document_id}/index", response_model=KnowledgeDocumentResponse)
async def index_knowledge_document(
    document_id: UUID,
    service: KnowledgeServiceDep,
    payload: KnowledgeIndexRequest | None = None,
) -> KnowledgeDocumentResponse:
    body = payload or KnowledgeIndexRequest()
    document = await service.mark_indexed(
        document_id,
        embedding_id=body.embedding_id,
        chunk_count=body.chunk_count,
    )
    return KnowledgeDocumentResponse.model_validate(document)


@router.post("/{document_id}/archive", response_model=KnowledgeDocumentResponse)
async def archive_knowledge_document(
    document_id: UUID,
    service: KnowledgeServiceDep,
) -> KnowledgeDocumentResponse:
    document = await service.archive(document_id)
    return KnowledgeDocumentResponse.model_validate(document)
