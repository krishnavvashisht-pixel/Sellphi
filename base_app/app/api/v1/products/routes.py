from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import DbSessionDep
from app.repositories.product import ProductRepository
from app.repositories.workspace import WorkspaceRepository
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.services.product import ProductService

router = APIRouter(prefix="/products", tags=["products"])


def get_product_service(db_session: DbSessionDep) -> ProductService:
    product_repository = ProductRepository(db_session)
    workspace_repository = WorkspaceRepository(db_session)
    return ProductService(
        product_repository=product_repository,
        workspace_repository=workspace_repository,
    )


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    payload: ProductCreate,
    service: ProductServiceDep,
) -> ProductResponse:
    product = await service.create(payload)
    return ProductResponse.model_validate(product)


@router.get("", response_model=ProductListResponse)
async def list_products(
    service: ProductServiceDep,
    workspace_id: Annotated[UUID, Query()],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
) -> ProductListResponse:
    products, total = await service.list(
        workspace_id=workspace_id,
        offset=offset,
        limit=limit,
        search=search,
    )
    return ProductListResponse(
        items=[ProductResponse.model_validate(product) for product in products],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    service: ProductServiceDep,
) -> ProductResponse:
    product = await service.get(product_id)
    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    service: ProductServiceDep,
) -> ProductResponse:
    product = await service.update(product_id, payload)
    return ProductResponse.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    service: ProductServiceDep,
) -> Response:
    await service.delete(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
