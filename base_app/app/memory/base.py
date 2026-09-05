from typing import Any, Protocol
from uuid import UUID


class MemoryStore(Protocol):
    async def get(self, workspace_id: UUID, key: str) -> dict[str, Any] | None:
        raise NotImplementedError

    async def set(self, workspace_id: UUID, key: str, value: dict[str, Any]) -> None:
        raise NotImplementedError

    async def delete(self, workspace_id: UUID, key: str) -> None:
        raise NotImplementedError
