from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import DbSessionDep
from app.repositories.opportunity import OpportunityRepository
from app.schemas.opportunity import OpportunityCreate, OpportunityResponse, OpportunityUpdate

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    payload: OpportunityCreate,
    session: DbSessionDep,
) -> OpportunityResponse:
    repo = OpportunityRepository(session)
    return await repo.create(payload)


@router.get("", response_model=list[OpportunityResponse])
async def list_opportunities(
    workspace_id: UUID,
    session: DbSessionDep,
) -> list[OpportunityResponse]:
    repo = OpportunityRepository(session)
    return await repo.list_by_workspace(workspace_id)


@router.patch("/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opportunity_id: UUID,
    payload: OpportunityUpdate,
    session: DbSessionDep,
) -> OpportunityResponse:
    repo = OpportunityRepository(session)
    opp = await repo.get_by_id(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return await repo.update(opp, payload)


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opportunity(
    opportunity_id: UUID,
    session: DbSessionDep,
) -> None:
    repo = OpportunityRepository(session)
    opp = await repo.get_by_id(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    await repo.delete(opp)
