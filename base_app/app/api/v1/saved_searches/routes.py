from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import DbSessionDep
from app.repositories.saved_search import SavedSearchRepository
from app.schemas.saved_search import SavedSearchCreate, SavedSearchResponse

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


@router.post("", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_search(
    payload: SavedSearchCreate,
    session: DbSessionDep,
) -> SavedSearchResponse:
    repo = SavedSearchRepository(session)
    return await repo.create(payload)


@router.get("", response_model=list[SavedSearchResponse])
async def list_saved_searches(
    workspace_id: UUID,
    session: DbSessionDep,
) -> list[SavedSearchResponse]:
    repo = SavedSearchRepository(session)
    return await repo.list_by_workspace(workspace_id)


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: UUID,
    session: DbSessionDep,
) -> None:
    repo = SavedSearchRepository(session)
    saved_search = await repo.get_by_id(search_id)
    if not saved_search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    await repo.delete(saved_search)
