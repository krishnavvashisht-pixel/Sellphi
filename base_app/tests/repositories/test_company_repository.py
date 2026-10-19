from uuid import uuid4

import pytest
from app.models.company import Company
from app.repositories.company import CompanyRepository


class RecordingSession:
    """Same convention as tests/repositories/test_mission_repository.py."""

    def __init__(self, existing: list[Company] | None = None) -> None:
        self.added: list[Company] = []
        self.existing = existing or []

    def add(self, instance: Company) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        for company in self.added:
            if company.id is None:
                company.id = uuid4()

    async def refresh(self, instance: Company) -> None:
        pass

    async def execute(self, statement: object) -> "FakeResult":
        return FakeResult(self.added + self.existing)

    async def commit(self) -> None:
        pass


class FakeResult:
    def __init__(self, pool: list[Company]) -> None:
        self._pool = pool

    def scalar_one_or_none(self) -> Company | None:
        return self._pool[0] if self._pool else None


@pytest.mark.asyncio
async def test_create_persists_a_company_and_assigns_an_id() -> None:
    session = RecordingSession()
    repository = CompanyRepository(session)  # type: ignore[arg-type]
    company = Company(name="Acme Corp")

    created = await repository.create(company)

    assert created.id is not None
    assert session.added == [company]


@pytest.mark.asyncio
async def test_get_by_id_returns_a_matching_company() -> None:
    existing = Company(name="Acme Corp")
    existing.id = uuid4()
    session = RecordingSession(existing=[existing])
    repository = CompanyRepository(session)  # type: ignore[arg-type]

    found = await repository.get_by_id(existing.id)

    assert found is existing


@pytest.mark.asyncio
async def test_get_by_name_returns_none_when_nothing_matches() -> None:
    session = RecordingSession(existing=[])
    repository = CompanyRepository(session)  # type: ignore[arg-type]

    found = await repository.get_by_name("Nonexistent Inc")

    assert found is None
