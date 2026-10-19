"""Orchestrates one raw item through classification and, if it clears the
score bar, storage — the "branch" step from the build plan (6.3.5):
score >= 0.5 -> a buying_signals row + BuyingSignalDetected event;
below -> discarded, logged as an event, nothing else created.
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.store import emit_event
from app.llm_client import LLMClient
from app.models.buying_signal import BuyingSignal
from app.models.company import Company
from app.models.mission import Mission
from app.repositories.buying_signal import BuyingSignalRepository
from app.repositories.company import CompanyRepository
from app.schemas.signal import RawSignalItem, SignalClassification
from app.services.signal_classifier import classify_signal

SIGNAL_SCORE_THRESHOLD = 0.5


async def find_or_create_company(
    company_repository: CompanyRepository,
    name: str,
    domain: str | None,
) -> Company:
    """The stub-then-enrich pattern: reuse the company if a signal already
    created it (case-insensitive name match — see CompanyRepository for
    why this isn't fuzzier), otherwise create a bare-minimum stub for
    prospect discovery to fill in later.
    """
    existing = await company_repository.get_by_name(name)
    if existing is not None:
        return existing

    company = Company(name=name, domain=domain)
    created = await company_repository.create(company)
    await company_repository.commit()
    return created


async def process_raw_signal(
    raw_item: RawSignalItem,
    mission: Mission,
    company_repository: CompanyRepository,
    buying_signal_repository: BuyingSignalRepository,
    session: AsyncSession,
    client: LLMClient | None = None,
) -> BuyingSignal | None:
    """Classify one raw item against a mission and, if it's a real signal,
    store it. Returns the created BuyingSignal, or None if discarded.
    """
    classification: SignalClassification = await classify_signal(raw_item, mission, client=client)

    if classification.score < SIGNAL_SCORE_THRESHOLD:
        await emit_event(
            session,
            entity_type="mission",
            entity_id=mission.id,
            event_type="BuyingSignalDiscarded",
            payload={
                "source": raw_item.source,
                "link": raw_item.link,
                "company_name": classification.company_name,
                "score": classification.score,
            },
        )
        return None

    company = await find_or_create_company(
        company_repository, classification.company_name, classification.company_domain
    )

    buying_signal = BuyingSignal(
        company_id=company.id,
        mission_id=mission.id,
        source=raw_item.source,
        signal_type=classification.signal_type,
        score=classification.score,
        urgency=classification.urgency,
        evidence=classification.evidence,
        sales_implication=classification.sales_implication,
        detected_at=raw_item.published_at or datetime.now(UTC),
    )
    created_signal = await buying_signal_repository.create(buying_signal)
    await buying_signal_repository.commit()

    await emit_event(
        session,
        entity_type="company",
        entity_id=company.id,
        event_type="BuyingSignalDetected",
        payload={
            "buying_signal_id": str(created_signal.id),
            "mission_id": str(mission.id),
            "score": classification.score,
            "signal_type": classification.signal_type.value,
        },
    )
    return created_signal
