from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import DbSessionDep
from app.repositories.icp import ICPRepository
from app.repositories.product import ProductRepository
from app.schemas.icp import (
    ICPCreate,
    ICPListResponse,
    ICPResponse,
    ICPUpdate,
)
from app.services.icp import ICPService

router = APIRouter(prefix="/icps", tags=["icps"])

# Separate router for the product-scoped default-icp endpoint
products_router = APIRouter(prefix="/products", tags=["icps"])


def get_icp_service(db_session: DbSessionDep) -> ICPService:
    icp_repository = ICPRepository(db_session)
    product_repository = ProductRepository(db_session)
    return ICPService(
        icp_repository=icp_repository,
        product_repository=product_repository,
    )


ICPServiceDep = Annotated[ICPService, Depends(get_icp_service)]


@router.post(
    "",
    response_model=ICPResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_icp(
    payload: ICPCreate,
    service: ICPServiceDep,
) -> ICPResponse:
    icp = await service.create(payload)
    return ICPResponse.model_validate(icp)


@router.get("", response_model=ICPListResponse)
async def list_icps(
    service: ICPServiceDep,
    product_id: Annotated[UUID, Query()],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> ICPListResponse:
    icps, total = await service.list(
        product_id=product_id,
        offset=offset,
        limit=limit,
        search=search,
        is_active=is_active,
    )
    return ICPListResponse(
        items=[ICPResponse.model_validate(icp) for icp in icps],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{icp_id}", response_model=ICPResponse)
async def get_icp(
    icp_id: UUID,
    service: ICPServiceDep,
) -> ICPResponse:
    icp = await service.get(icp_id)
    return ICPResponse.model_validate(icp)


@router.patch("/{icp_id}", response_model=ICPResponse)
async def update_icp(
    icp_id: UUID,
    payload: ICPUpdate,
    service: ICPServiceDep,
) -> ICPResponse:
    icp = await service.update(icp_id, payload)
    return ICPResponse.model_validate(icp)


@router.delete("/{icp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_icp(
    icp_id: UUID,
    service: ICPServiceDep,
) -> Response:
    await service.delete(icp_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Product-scoped endpoint ───────────────────────────────────────────────────

@products_router.get("/{product_id}/default-icp", response_model=ICPResponse, tags=["icps"])
async def get_default_icp(
    product_id: UUID,
    service: ICPServiceDep,
) -> ICPResponse:
    icp = await service.get_default_for_product(product_id)
    return ICPResponse.model_validate(icp)
