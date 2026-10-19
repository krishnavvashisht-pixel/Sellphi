"""Tests for the branch logic: score >= 0.5 stores a signal (and reuses or
creates the company stub) + emits BuyingSignalDetected; below discards
and emits only BuyingSignalDiscarded. This is the heart of signal
detection's "Done when" criterion.
"""

import json
from uuid import uuid4

import pytest
from app.models.buying_signal import BuyingSignal
from app.models.company import Company
from app.schemas.signal import RawSignalItem
from app.services.signal_detection import (
    SIGNAL_SCORE_THRESHOLD,
    find_or_create_company,
    process_raw_signal,
)


class FakeGeminiClient:
    def __init__(self, canned_response: dict) -> None:
        self.canned_response = json.dumps(canned_response)

    async def generate_structured(self, prompt: str, schema: type) -> object:
        return schema.model_validate_json(self.canned_response)


class FakeCompanyRepository:
    """A real fake, unlike the repository-level tests — this one actually
    implements find-by-name and create against an in-memory list, since
    find_or_create_company's reuse logic is exactly what needs verifying.
    """

    def __init__(self, existing: list[Company] | None = None) -> None:
        self.companies = existing or []
        self.commits = 0

    async def get_by_name(self, name: str) -> Company | None:
        return next((c for c in self.companies if c.name.lower() == name.lower()), None)

    async def create(self, company: Company) -> Company:
        company.id = company.id or uuid4()
        self.companies.append(company)
        return company

    async def commit(self) -> None:
        self.commits += 1


class FakeBuyingSignalRepository:
    def __init__(self) -> None:
        self.signals: list[BuyingSignal] = []
        self.commits = 0

    async def create(self, signal: BuyingSignal) -> BuyingSignal:
        signal.id = signal.id or uuid4()
        self.signals.append(signal)
        return signal

    async def commit(self) -> None:
        self.commits += 1


class RecordingSession:
    """Only used for emit_event here — same convention as tests/events/test_store.py."""

    def __init__(self) -> None:
        self.events: list[object] = []

    def add(self, instance: object) -> None:
        self.events.append(instance)

    async def flush(self) -> None:
        pass

    async def refresh(self, instance: object) -> None:
        pass


STRONG_SIGNAL = {
    "company_name": "Acme Corp",
    "company_domain": "acme.com",
    "score": 0.9,
    "signal_type": "funding",
    "urgency": "high",
    "icp_match": True,
    "evidence": "Acme Corp announced a $10M Series A funding round.",
    "sales_implication": "Newly funded companies often need to scale data infrastructure.",
}

WEAK_SIGNAL = {
    "company_name": "Sweet Treats Bakery",
    "company_domain": None,
    "score": 0.05,
    "signal_type": "other",
    "urgency": "low",
    "icp_match": False,
    "evidence": "A local bakery won a pie contest.",
    "sales_implication": "Not relevant.",
}

RAW_ITEM = RawSignalItem(
    title="Acme Corp raises $10M Series A",
    link="https://example.com/acme-series-a",
    summary="Acme Corp announced funding.",
)


@pytest.mark.asyncio
async def test_a_strong_signal_creates_a_company_and_a_buying_signal(sample_mission) -> None:  # noqa: ANN001
    company_repository = FakeCompanyRepository()
    signal_repository = FakeBuyingSignalRepository()
    session = RecordingSession()
    client = FakeGeminiClient(STRONG_SIGNAL)

    result = await process_raw_signal(
        RAW_ITEM,
        sample_mission,
        company_repository,  # type: ignore[arg-type]
        signal_repository,  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
    )

    assert result is not None
    assert result.score == 0.9
    assert result.evidence == STRONG_SIGNAL["evidence"]
    assert result.sales_implication == STRONG_SIGNAL["sales_implication"]
    assert len(company_repository.companies) == 1
    assert company_repository.companies[0].name == "Acme Corp"
    assert result.company_id == company_repository.companies[0].id
    assert signal_repository.commits == 1


@pytest.mark.asyncio
async def test_a_weak_signal_is_discarded_and_creates_nothing(sample_mission) -> None:  # noqa: ANN001
    company_repository = FakeCompanyRepository()
    signal_repository = FakeBuyingSignalRepository()
    session = RecordingSession()
    client = FakeGeminiClient(WEAK_SIGNAL)

    result = await process_raw_signal(
        RAW_ITEM,
        sample_mission,
        company_repository,  # type: ignore[arg-type]
        signal_repository,  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
    )

    assert result is None
    assert company_repository.companies == []
    assert signal_repository.signals == []
    # Still logged — discards aren't silent, just don't create real records.
    assert len(session.events) == 1


@pytest.mark.asyncio
async def test_a_signal_exactly_at_the_threshold_is_kept(sample_mission) -> None:  # noqa: ANN001
    at_threshold = {**STRONG_SIGNAL, "score": SIGNAL_SCORE_THRESHOLD}
    company_repository = FakeCompanyRepository()
    signal_repository = FakeBuyingSignalRepository()
    session = RecordingSession()
    client = FakeGeminiClient(at_threshold)

    result = await process_raw_signal(
        RAW_ITEM,
        sample_mission,
        company_repository,  # type: ignore[arg-type]
        signal_repository,  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
    )

    assert result is not None


@pytest.mark.asyncio
async def test_a_second_signal_about_the_same_company_reuses_it(sample_mission) -> None:  # noqa: ANN001
    company_repository = FakeCompanyRepository()
    signal_repository = FakeBuyingSignalRepository()
    session = RecordingSession()

    first = await process_raw_signal(
        RAW_ITEM,
        sample_mission,
        company_repository,  # type: ignore[arg-type]
        signal_repository,  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
        client=FakeGeminiClient(STRONG_SIGNAL),  # type: ignore[arg-type]
    )
    second_signal_data = {**STRONG_SIGNAL, "evidence": "Acme Corp also hired a new VP."}
    second = await process_raw_signal(
        RawSignalItem(
            title="Acme Corp hires VP",
            link="https://example.com/acme-vp",
            summary="Acme Corp hired a VP.",
        ),
        sample_mission,
        company_repository,  # type: ignore[arg-type]
        signal_repository,  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
        client=FakeGeminiClient(second_signal_data),  # type: ignore[arg-type]
    )

    assert len(company_repository.companies) == 1  # not duplicated
    assert first.company_id == second.company_id
    assert len(signal_repository.signals) == 2


@pytest.mark.asyncio
async def test_find_or_create_company_creates_when_none_exists() -> None:
    company_repository = FakeCompanyRepository()

    company = await find_or_create_company(company_repository, "New Co", "newco.com")  # type: ignore[arg-type]

    assert company.name == "New Co"
    assert len(company_repository.companies) == 1


@pytest.mark.asyncio
async def test_find_or_create_company_reuses_case_insensitively() -> None:
    existing = Company(name="Acme Corp")
    existing.id = uuid4()
    company_repository = FakeCompanyRepository(existing=[existing])

    company = await find_or_create_company(company_repository, "ACME CORP", None)  # type: ignore[arg-type]

    assert company.id == existing.id
    assert len(company_repository.companies) == 1
