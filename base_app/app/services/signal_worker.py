from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm_client import LLMClient
from app.models.buying_signal import BuyingSignal
from app.repositories.buying_signal import BuyingSignalRepository
from app.repositories.company import CompanyRepository
from app.repositories.mission import MissionRepository
from app.schemas.signal import RawSignalItem
from app.services.signal_detection import process_raw_signal


async def classify_and_store(
    raw_item: RawSignalItem,
    mission_id: UUID,
    mission_repository: MissionRepository,
    company_repository: CompanyRepository,
    buying_signal_repository: BuyingSignalRepository,
    session: AsyncSession,
    client: LLMClient | None = None,
) -> BuyingSignal | None:
    """What the queued worker job actually does, once it wakes up: look up
    the mission, then hand off to the already-tested classify/branch/store
    logic. Split out from the RQ job wiring in signal_queue.py so this part
    — the part with real logic — is unit-testable without a real Redis or
    Postgres connection.
    """
    mission = await mission_repository.get_by_id(mission_id)
    if mission is None:
        # The mission was deleted or never existed by the time this job
        # ran — nothing sensible to classify against, so do nothing rather
        # than guess or raise and retry forever.
        return None

    return await process_raw_signal(
        raw_item,
        mission,
        company_repository,
        buying_signal_repository,
        session,
        client=client,
    )
