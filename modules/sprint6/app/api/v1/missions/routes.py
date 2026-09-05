from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import DbSessionDep
from app.models.mission import MissionStatus
from app.repositories.buyer_persona import BuyerPersonaRepository
from app.repositories.icp import ICPRepository
from app.repositories.mission import MissionRepository
from app.repositories.product import ProductRepository
from app.schemas.mission import (
    MissionCreate,
    MissionListResponse,
    MissionResponse,
    MissionUpdate,
)
from app.services.mission import MissionService

router = APIRouter(prefix="/missions", tags=["missions"])


def get_mission_service(db_session: DbSessionDep) -> MissionService:
    return MissionService(
        mission_repository=MissionRepository(db_session),
        product_repository=ProductRepository(db_session),
        icp_repository=ICPRepository(db_session),
        buyer_persona_repository=BuyerPersonaRepository(db_session),
    )


MissionServiceDep = Annotated[MissionService, Depends(get_mission_service)]


@router.post(
    "",
    response_model=MissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mission(
    payload: MissionCreate,
    service: MissionServiceDep,
) -> MissionResponse:
    mission = await service.create(payload)
    return MissionResponse.model_validate(mission)


@router.get("", response_model=MissionListResponse)
async def list_missions(
    service: MissionServiceDep,
    product_id: Annotated[UUID, Query()],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    status_filter: Annotated[MissionStatus | None, Query(alias="status")] = None,
) -> MissionListResponse:
    missions, total = await service.list(
        product_id=product_id,
        offset=offset,
        limit=limit,
        search=search,
        status=status_filter,
    )
    return MissionListResponse(
        items=[MissionResponse.model_validate(mission) for mission in missions],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{mission_id}", response_model=MissionResponse)
async def get_mission(
    mission_id: UUID,
    service: MissionServiceDep,
) -> MissionResponse:
    mission = await service.get(mission_id)
    return MissionResponse.model_validate(mission)


@router.patch("/{mission_id}", response_model=MissionResponse)
async def update_mission(
    mission_id: UUID,
    payload: MissionUpdate,
    service: MissionServiceDep,
) -> MissionResponse:
    mission = await service.update(mission_id, payload)
    return MissionResponse.model_validate(mission)


@router.delete("/{mission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mission(
    mission_id: UUID,
    service: MissionServiceDep,
) -> Response:
    await service.delete(mission_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Status-transition actions ─────────────────────────────────────────────────

@router.post("/{mission_id}/pause", response_model=MissionResponse)
async def pause_mission(
    mission_id: UUID,
    service: MissionServiceDep,
) -> MissionResponse:
    mission = await service.pause(mission_id)
    return MissionResponse.model_validate(mission)


@router.post("/{mission_id}/resume", response_model=MissionResponse)
async def resume_mission(
    mission_id: UUID,
    service: MissionServiceDep,
) -> MissionResponse:
    mission = await service.resume(mission_id)
    return MissionResponse.model_validate(mission)


@router.post("/{mission_id}/complete", response_model=MissionResponse)
async def complete_mission(
    mission_id: UUID,
    service: MissionServiceDep,
) -> MissionResponse:
    mission = await service.complete(mission_id)
    return MissionResponse.model_validate(mission)


@router.post("/{mission_id}/run", response_model=MissionResponse)
async def run_mission(
    mission_id: UUID,
    service: MissionServiceDep,
) -> MissionResponse:
    mission = await service.run(mission_id)
    return MissionResponse.model_validate(mission)
