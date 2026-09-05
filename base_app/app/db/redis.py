from collections.abc import AsyncIterator

from redis.asyncio import Redis

from app.core.config import get_settings

_redis_client: Redis | None = None


async def init_redis_pool(redis_url: str | None = None) -> Redis:
    global _redis_client

    if _redis_client is None:
        settings = get_settings()
        _redis_client = Redis.from_url(
            redis_url or settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )

    return _redis_client


async def close_redis_pool() -> None:
    global _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def get_redis_client() -> AsyncIterator[Redis]:
    client = await init_redis_pool()
    yield client
