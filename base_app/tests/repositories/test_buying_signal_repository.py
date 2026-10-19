from uuid import uuid4

import pytest
from app.models.buying_signal import BuyingSignal, SignalType, SignalUrgency
from app.repositories.buying_signal import BuyingSignalRepository


class RecordingSession:
    def __init__(self) -> None:
        self.added: list[BuyingSignal] = []

    def add(self, instance: BuyingSignal) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        for signal in self.added:
            if signal.id is None:
                signal.id = uuid4()

    async def refresh(self, instance: BuyingSignal) -> None:
        pass

    async def commit(self) -> None:
        pass


@pytest.mark.asyncio
async def test_create_persists_a_buying_signal_and_assigns_an_id() -> None:
    session = RecordingSession()
    repository = BuyingSignalRepository(session)  # type: ignore[arg-type]
    signal = BuyingSignal(
        company_id=uuid4(),
        mission_id=uuid4(),
        source="google_news_rss",
        signal_type=SignalType.FUNDING,
        score=0.8,
        urgency=SignalUrgency.HIGH,
        evidence="Acme Corp announced a $10M Series A.",
        sales_implication="They'll need to scale their data infra soon.",
    )

    created = await repository.create(signal)

    assert created.id is not None
    assert session.added == [signal]
