from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import DbSessionDep
from app.repositories.workspace import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate
from app.services.workspace import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def get_workspace_service(db_session: DbSessionDep) -> WorkspaceService:
    repository = WorkspaceRepository(db_session)
    return WorkspaceService(repository)


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    payload: WorkspaceCreate,
    service: WorkspaceServiceDep,
) -> WorkspaceResponse:
    workspace = await service.create(payload)
    return WorkspaceResponse.model_validate(workspace)


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    service: WorkspaceServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[WorkspaceResponse]:
    workspaces = await service.list(offset=offset, limit=limit)
    return [WorkspaceResponse.model_validate(workspace) for workspace in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    service: WorkspaceServiceDep,
) -> WorkspaceResponse:
    workspace = await service.get(workspace_id)
    return WorkspaceResponse.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdate,
    service: WorkspaceServiceDep,
) -> WorkspaceResponse:
    workspace = await service.update(workspace_id, payload)
    return WorkspaceResponse.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    service: WorkspaceServiceDep,
) -> Response:
    await service.delete(workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
