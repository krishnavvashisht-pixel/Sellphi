from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, Field


class AgentContext(BaseModel):
    workspace_id: UUID | None = None
    actor_id: UUID | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class Agent(Protocol):
    name: str

    async def run(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError
