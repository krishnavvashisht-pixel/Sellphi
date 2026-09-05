from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        return self.__class__.__name__


class EventBus(Protocol):
    async def publish(self, event: DomainEvent) -> None:
        raise NotImplementedError

    async def publish_many(self, events: list[DomainEvent]) -> None:
        raise NotImplementedError
