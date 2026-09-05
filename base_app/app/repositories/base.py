from typing import Protocol, TypeVar
from uuid import UUID

ModelT = TypeVar("ModelT")


class Repository[ModelT](Protocol):
    async def get_by_id(self, entity_id: UUID) -> ModelT | None:
        raise NotImplementedError

    async def add(self, entity: ModelT) -> ModelT:
        raise NotImplementedError

    async def delete(self, entity: ModelT) -> None:
        raise NotImplementedError
