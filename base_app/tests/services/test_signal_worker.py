import json
from uuid import uuid4

import pytest
from app.models.company import Company
from app.models.mission import Mission, MissionStatus
from app.schemas.signal import RawSignalItem
from app.services.signal_worker import classify_and_store


class FakeGeminiClient:
    def __init__(self, canned_response: dict) -> None:
        self.canned_response = json.dumps(canned_response)

    async def generate_structured(self, prompt: str, schema: type) -> object:
        return schema.model_validate_json(self.canned_response)


class FakeMissionRepository:
    def __init__(self, mission: Mission | None = None) -> None:
        self.mission = mission

    async def get_by_id(self, mission_id) -> Mission | None:  # noqa: ANN001
        return self.mission if self.mission and self.mission.id == mission_id else None


class FakeCompanyRepository:
    def __init__(self) -> None:
        self.companies: list[Company] = []

    async def get_by_name(self, name: str) -> Company | None:
        return next((c for c in self.companies if c.name.lower() == name.lower()), None)

    async def create(self, company: Company) -> Company:
        company.id = company.id or uuid4()
        self.companies.append(company)
        return company

    async def commit(self) -> None:
        pass


class FakeBuyingSignalRepository:
    def __init__(self) -> None:
        self.signals: list[object] = []

    async def create(self, signal: object) -> object:
        signal.id = uuid4()  # type: ignore[attr-defined]
        self.signals.append(signal)
        return signal

    async def commit(self) -> None:
        pass


class RecordingSession:
    def add(self, instance: object) -> None:
        pass

    async def flush(self) -> None:
        pass

    async def refresh(self, instance: object) -> None:
        pass


STRONG_SIGNAL = {
    "company_name": "Acme Corp",
    "company_domain": None,
    "score": 0.9,
    "signal_type": "funding",
    "urgency": "high",
    "icp_match": True,
    "evidence": "Acme Corp raised a Series A.",
    "sales_implication": "Worth reaching out.",
}


@pytest.mark.asyncio
async def test_classify_and_store_processes_the_signal_when_mission_exists(sample_mission) -> None:  # noqa: ANN001
    sample_mission.id = uuid4()
    mission_repository = FakeMissionRepository(mission=sample_mission)
    company_repository = FakeCompanyRepository()
    signal_repository = FakeBuyingSignalRepository()
    session = RecordingSession()
    raw_item = RawSignalItem(title="Acme raises funding", link="https://example.com/x")

    result = await classify_and_store(
        raw_item,
        sample_mission.id,
        mission_repository,  # type: ignore[arg-type]
        company_repository,  # type: ignore[arg-type]
        signal_repository,  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
        client=FakeGeminiClient(STRONG_SIGNAL),  # type: ignore[arg-type]
    )

    assert result is not None
    assert len(signal_repository.signals) == 1


@pytest.mark.asyncio
async def test_classify_and_store_does_nothing_when_the_mission_is_gone() -> None:
    mission_repository = FakeMissionRepository(mission=None)
    company_repository = FakeCompanyRepository()
    signal_repository = FakeBuyingSignalRepository()
    session = RecordingSession()
    raw_item = RawSignalItem(title="Acme raises funding", link="https://example.com/x")

    result = await classify_and_store(
        raw_item,
        uuid4(),
        mission_repository,  # type: ignore[arg-type]
        company_repository,  # type: ignore[arg-type]
        signal_repository,  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
        client=FakeGeminiClient(STRONG_SIGNAL),  # type: ignore[arg-type]
    )

    assert result is None
    assert signal_repository.signals == []
