from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import DbSessionDep
from app.models.buyer_persona import BuyingRole, PersonaStatus, SeniorityLevel
from app.repositories.buyer_persona import BuyerPersonaRepository
from app.repositories.product import ProductRepository
from app.schemas.buyer_persona import (
    BuyerPersonaCreate,
    BuyerPersonaListResponse,
    BuyerPersonaResponse,
    BuyerPersonaUpdate,
)
from app.services.buyer_persona import BuyerPersonaService

router = APIRouter(prefix="/buyer-personas", tags=["buyer-personas"])

# Separate router for the product-scoped default-persona endpoint
products_router = APIRouter(prefix="/products", tags=["buyer-personas"])


def get_buyer_persona_service(db_session: DbSessionDep) -> BuyerPersonaService:
    buyer_persona_repository = BuyerPersonaRepository(db_session)
    product_repository = ProductRepository(db_session)
    return BuyerPersonaService(
        buyer_persona_repository=buyer_persona_repository,
        product_repository=product_repository,
    )


BuyerPersonaServiceDep = Annotated[BuyerPersonaService, Depends(get_buyer_persona_service)]


@router.post(
    "",
    response_model=BuyerPersonaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_buyer_persona(
    payload: BuyerPersonaCreate,
    service: BuyerPersonaServiceDep,
) -> BuyerPersonaResponse:
    persona = await service.create(payload)
    return BuyerPersonaResponse.model_validate(persona)


@router.get("", response_model=BuyerPersonaListResponse)
async def list_buyer_personas(
    service: BuyerPersonaServiceDep,
    product_id: Annotated[UUID, Query()],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    status_filter: Annotated[PersonaStatus | None, Query(alias="status")] = None,
    seniority: Annotated[SeniorityLevel | None, Query()] = None,
    buying_role: Annotated[BuyingRole | None, Query()] = None,
) -> BuyerPersonaListResponse:
    personas, total = await service.list(
        product_id=product_id,
        offset=offset,
        limit=limit,
        search=search,
        status=status_filter,
        seniority=seniority,
        buying_role=buying_role,
    )
    return BuyerPersonaListResponse(
        items=[BuyerPersonaResponse.model_validate(persona) for persona in personas],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{persona_id}", response_model=BuyerPersonaResponse)
async def get_buyer_persona(
    persona_id: UUID,
    service: BuyerPersonaServiceDep,
) -> BuyerPersonaResponse:
    persona = await service.get(persona_id)
    return BuyerPersonaResponse.model_validate(persona)


@router.patch("/{persona_id}", response_model=BuyerPersonaResponse)
async def update_buyer_persona(
    persona_id: UUID,
    payload: BuyerPersonaUpdate,
    service: BuyerPersonaServiceDep,
) -> BuyerPersonaResponse:
    persona = await service.update(persona_id, payload)
    return BuyerPersonaResponse.model_validate(persona)


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_buyer_persona(
    persona_id: UUID,
    service: BuyerPersonaServiceDep,
) -> Response:
    await service.delete(persona_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Product-scoped endpoint ───────────────────────────────────────────────────

@products_router.get(
    "/{product_id}/default-persona",
    response_model=BuyerPersonaResponse,
    tags=["buyer-personas"],
)
async def get_default_buyer_persona(
    product_id: UUID,
    service: BuyerPersonaServiceDep,
) -> BuyerPersonaResponse:
    persona = await service.get_default_for_product(product_id)
    return BuyerPersonaResponse.model_validate(persona)
