"""RQ queue wiring for signal detection: "RSS -> Redis/RQ queue" (build
plan 6.3.3). Deliberately thin — RQ needs a synchronous Redis connection
(unlike the rest of the app, which uses redis.asyncio), and a queued job
must itself be a synchronous, importable-by-name function, so this file's
only job is bridging that to the real async logic in signal_worker.py.

Not unit tested here: actually enqueuing/running a job needs a real Redis
server and a real Postgres database, neither of which exist in this
sandbox. app/services/signal_worker.py (the part with actual logic) is
fully unit tested; this file is thin enough that the honest way to verify
it is to actually run it (see PROJECT_GUIDE.md).
"""

import asyncio
from uuid import UUID

import redis
from rq import Queue

from app.core.config import get_settings
from app.schemas.signal import RawSignalItem

SIGNAL_QUEUE_NAME = "signals"


def get_sync_redis_connection(redis_url: str | None = None) -> redis.Redis:
    """RQ's Queue/Worker need the classic synchronous redis-py client —
    the app's existing app/db/redis.py is redis.asyncio, which RQ can't
    use directly.
    """
    return redis.Redis.from_url(redis_url or get_settings().redis_url)


def get_signal_queue(connection: redis.Redis | None = None) -> Queue:
    return Queue(SIGNAL_QUEUE_NAME, connection=connection or get_sync_redis_connection())


def enqueue_raw_signal(queue: Queue, raw_item: RawSignalItem, mission_id: UUID) -> None:
    """Push one raw item onto the queue. Ingestion calls this and moves on
    immediately — nobody waits around for classification.
    """
    queue.enqueue(classify_and_store_job, raw_item.model_dump(mode="json"), str(mission_id))


def classify_and_store_job(raw_item_data: dict, mission_id: str) -> None:
    """The actual function RQ calls when a worker picks up a job. Must be
    synchronous (RQ workers run jobs synchronously) and importable by
    name (RQ serializes a reference to this function, not a closure) —
    hence the asyncio.run() wrapper around the real async work.
    """
    asyncio.run(_run_classify_and_store(raw_item_data, mission_id))


async def _run_classify_and_store(raw_item_data: dict, mission_id: str) -> None:
    from app.db.session import AsyncSessionLocal
    from app.repositories.buying_signal import BuyingSignalRepository
    from app.repositories.company import CompanyRepository
    from app.repositories.mission import MissionRepository
    from app.services.signal_worker import classify_and_store

    raw_item = RawSignalItem.model_validate(raw_item_data)

    async with AsyncSessionLocal() as session:
        await classify_and_store(
            raw_item,
            UUID(mission_id),
            MissionRepository(session),
            CompanyRepository(session),
            BuyingSignalRepository(session),
            session,
        )
