from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
@dataclass(frozen=True)
class ResearchCreated: research_id: UUID; company_id: UUID; version: int; created_by: UUID; timestamp: datetime = field(default_factory=datetime.utcnow)
@dataclass(frozen=True)
class ResearchUpdated: research_id: UUID; version: int; updated_fields: list[str]; timestamp: datetime = field(default_factory=datetime.utcnow)
@dataclass(frozen=True)
class ResearchScored: research_id: UUID; ai_score: int; timestamp: datetime = field(default_factory=datetime.utcnow)
@dataclass(frozen=True)
class ResearchDeleted: research_id: UUID; deleted_by: UUID; timestamp: datetime = field(default_factory=datetime.utcnow)
