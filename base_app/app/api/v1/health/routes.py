from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import DbSessionDep, RedisDep
from app.core.config import get_settings
from app.schemas.health import HealthResponse
from app.services.health import HealthService

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check(db_session: DbSessionDep, redis_client: RedisDep) -> HealthResponse:
    settings = get_settings()
    service = HealthService(db_session=db_session, redis_client=redis_client)
    response = await service.check(version=settings.app_version)

    if response.status != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.model_dump(),
        )

    return response
