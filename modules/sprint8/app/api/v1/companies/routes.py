from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import DbSessionDep
from app.models.company import CompanyStatus, FundingStage
from app.repositories.company import CompanyRepository
from app.repositories.mission import MissionRepository
from app.repositories.product import ProductRepository
from app.repositories.workspace import WorkspaceRepository
from app.schemas.company import (
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
)
from app.services.company import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


def get_company_service(db_session: DbSessionDep) -> CompanyService:
    return CompanyService(
        company_repository=CompanyRepository(db_session),
        workspace_repository=WorkspaceRepository(db_session),
        mission_repository=MissionRepository(db_session),
        product_repository=ProductRepository(db_session),
    )


CompanyServiceDep = Annotated[CompanyService, Depends(get_company_service)]


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_company(
    payload: CompanyCreate,
    service: CompanyServiceDep,
) -> CompanyResponse:
    company = await service.create(payload)
    return CompanyResponse.model_validate(company)


@router.get("", response_model=CompanyListResponse)
async def list_companies(
    service: CompanyServiceDep,
    workspace_id: Annotated[UUID, Query()],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    industry: Annotated[str | None, Query(max_length=255)] = None,
    status_filter: Annotated[CompanyStatus | None, Query(alias="status")] = None,
    funding_stage: Annotated[FundingStage | None, Query()] = None,
    company_size: Annotated[str | None, Query(max_length=64)] = None,
    country: Annotated[str | None, Query(max_length=128)] = None,
    mission_id: Annotated[UUID | None, Query()] = None,
) -> CompanyListResponse:
    companies, total = await service.list(
        workspace_id=workspace_id,
        offset=offset,
        limit=limit,
        search=search,
        industry=industry,
        status=status_filter,
        funding_stage=funding_stage,
        company_size=company_size,
        country=country,
        mission_id=mission_id,
    )
    return CompanyListResponse(
        items=[CompanyResponse.model_validate(company) for company in companies],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    service: CompanyServiceDep,
) -> CompanyResponse:
    company = await service.get(company_id)
    return CompanyResponse.model_validate(company)


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    service: CompanyServiceDep,
) -> CompanyResponse:
    company = await service.update(company_id, payload)
    return CompanyResponse.model_validate(company)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID,
    service: CompanyServiceDep,
) -> Response:
    await service.delete(company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Lifecycle actions ──────────────────────────────────────────────────────────

@router.post("/{company_id}/archive", response_model=CompanyResponse)
async def archive_company(
    company_id: UUID,
    service: CompanyServiceDep,
) -> CompanyResponse:
    company = await service.archive(company_id)
    return CompanyResponse.model_validate(company)


@router.post("/{company_id}/restore", response_model=CompanyResponse)
async def restore_company(
    company_id: UUID,
    service: CompanyServiceDep,
) -> CompanyResponse:
    company = await service.restore(company_id)
    return CompanyResponse.model_validate(company)
