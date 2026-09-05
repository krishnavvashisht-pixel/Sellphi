from typing import Any, Protocol

from pydantic import BaseModel, Field


class WorkerJob(BaseModel):
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


class Worker(Protocol):
    async def enqueue(self, job: WorkerJob) -> None:
        raise NotImplementedError
