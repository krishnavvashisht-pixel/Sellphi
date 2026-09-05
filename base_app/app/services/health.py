from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.health import ConnectionStatus, HealthResponse, ServiceStatus


class HealthService:
    def __init__(self, db_session: AsyncSession, redis_client: Redis) -> None:
        self._db_session = db_session
        self._redis_client = redis_client

    async def check(self, version: str) -> HealthResponse:
        database_status = await self._check_database()
        redis_status = await self._check_redis()
        overall_status: ServiceStatus = (
            "healthy"
            if database_status == "connected" and redis_status == "connected"
            else "unhealthy"
        )

        return HealthResponse(
            status=overall_status,
            database=database_status,
            redis=redis_status,
            version=version,
        )

    async def _check_database(self) -> ConnectionStatus:
        try:
            await self._db_session.execute(text("SELECT 1"))
        except Exception:
            return "disconnected"
        return "connected"

    async def _check_redis(self) -> ConnectionStatus:
        try:
            ping_result = await self._redis_client.ping()
        except Exception:
            return "disconnected"
        return "connected" if ping_result else "disconnected"
