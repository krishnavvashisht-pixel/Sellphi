from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import DbSessionDep
from app.models.buyer_persona import SeniorityLevel
from app.models.contact import ContactStatus, PreferredChannel, RelationshipStatus
from app.repositories.buyer_persona import BuyerPersonaRepository
from app.repositories.company import CompanyRepository
from app.repositories.contact import ContactRepository
from app.repositories.product import ProductRepository
from app.schemas.contact import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
)
from app.services.contact import ContactService

router = APIRouter(prefix="/contacts", tags=["contacts"])


def get_contact_service(db_session: DbSessionDep) -> ContactService:
    return ContactService(
        contact_repository=ContactRepository(db_session),
        company_repository=CompanyRepository(db_session),
        buyer_persona_repository=BuyerPersonaRepository(db_session),
        product_repository=ProductRepository(db_session),
    )


ContactServiceDep = Annotated[ContactService, Depends(get_contact_service)]


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_contact(
    payload: ContactCreate,
    service: ContactServiceDep,
) -> ContactResponse:
    contact = await service.create(payload)
    return ContactResponse.model_validate(contact)


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    service: ContactServiceDep,
    company_id: Annotated[UUID, Query()],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    department: Annotated[str | None, Query(max_length=255)] = None,
    seniority: Annotated[SeniorityLevel | None, Query()] = None,
    relationship_status: Annotated[RelationshipStatus | None, Query()] = None,
    preferred_channel: Annotated[PreferredChannel | None, Query()] = None,
    status_filter: Annotated[ContactStatus | None, Query(alias="status")] = None,
) -> ContactListResponse:
    contacts, total = await service.list(
        company_id=company_id,
        offset=offset,
        limit=limit,
        search=search,
        department=department,
        seniority=seniority,
        relationship_status=relationship_status,
        preferred_channel=preferred_channel,
        status=status_filter,
    )
    return ContactListResponse(
        items=[ContactResponse.model_validate(contact) for contact in contacts],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: UUID,
    service: ContactServiceDep,
) -> ContactResponse:
    contact = await service.get(contact_id)
    return ContactResponse.model_validate(contact)


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID,
    payload: ContactUpdate,
    service: ContactServiceDep,
) -> ContactResponse:
    contact = await service.update(contact_id, payload)
    return ContactResponse.model_validate(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID,
    service: ContactServiceDep,
) -> Response:
    await service.delete(contact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Lifecycle actions ──────────────────────────────────────────────────────────

@router.post("/{contact_id}/archive", response_model=ContactResponse)
async def archive_contact(
    contact_id: UUID,
    service: ContactServiceDep,
) -> ContactResponse:
    contact = await service.archive(contact_id)
    return ContactResponse.model_validate(contact)


@router.post("/{contact_id}/restore", response_model=ContactResponse)
async def restore_contact(
    contact_id: UUID,
    service: ContactServiceDep,
) -> ContactResponse:
    contact = await service.restore(contact_id)
    return ContactResponse.model_validate(contact)
