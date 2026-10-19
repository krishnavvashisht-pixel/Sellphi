from uuid import uuid4

import pytest
from app.models.mission import Mission, MissionStatus
from app.repositories.mission import MissionRepository


class RecordingSession:
    """Fake AsyncSession — same convention as tests/events/test_store.py."""

    def __init__(self, existing: list[Mission] | None = None) -> None:
        self.added: list[Mission] = []
        self.existing = existing or []

    def add(self, instance: Mission) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        for mission in self.added:
            if mission.id is None:
                mission.id = uuid4()

    async def refresh(self, instance: Mission) -> None:
        pass

    async def execute(self, statement: object) -> "FakeResult":
        pool = self.added + self.existing
        return FakeResult(pool)

    async def commit(self) -> None:
        pass


class FakeResult:
    def __init__(self, pool: list[Mission]) -> None:
        self._pool = pool

    def scalar_one_or_none(self) -> Mission | None:
        # Good enough for these tests: whatever was added/seeded is "found".
        return self._pool[0] if self._pool else None


@pytest.mark.asyncio
async def test_create_persists_a_mission_and_assigns_an_id() -> None:
    session = RecordingSession()
    repository = MissionRepository(session)  # type: ignore[arg-type]
    mission = Mission(name="Find companies that just raised funding")

    created = await repository.create(mission)

    assert created.id is not None
    assert session.added == [mission]


@pytest.mark.asyncio
async def test_get_by_id_returns_a_matching_mission() -> None:
    existing = Mission(name="Find companies that just raised funding", status=MissionStatus.ACTIVE)
    existing.id = uuid4()
    session = RecordingSession(existing=[existing])
    repository = MissionRepository(session)  # type: ignore[arg-type]

    found = await repository.get_by_id(existing.id)

    assert found is existing


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_nothing_matches() -> None:
    session = RecordingSession(existing=[])
    repository = MissionRepository(session)  # type: ignore[arg-type]

    found = await repository.get_by_id(uuid4())

    assert found is None
