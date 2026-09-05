from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
@dataclass(frozen=True)
class BuyingSignalCreated: signal_id: UUID; company_id: UUID; created_by: UUID; timestamp: datetime = field(default_factory=datetime.utcnow)
@dataclass(frozen=True)
class BuyingSignalUpdated: signal_id: UUID; updated_fields: list[str]; timestamp: datetime = field(default_factory=datetime.utcnow)
@dataclass(frozen=True)
class BuyingSignalVerified: signal_id: UUID; verified_by: UUID; timestamp: datetime = field(default_factory=datetime.utcnow)
@dataclass(frozen=True)
class BuyingSignalArchived: signal_id: UUID; timestamp: datetime = field(default_factory=datetime.utcnow)
@dataclass(frozen=True)
class BuyingSignalExpired: signal_id: UUID; timestamp: datetime = field(default_factory=datetime.utcnow)
@dataclass(frozen=True)
class BuyingSignalDeleted: signal_id: UUID; deleted_by: UUID; timestamp: datetime = field(default_factory=datetime.utcnow)
@dataclass(frozen=True)
class BuyingSignalScored: signal_id: UUID; freshness_score: int; ai_score: int; timestamp: datetime = field(default_factory=datetime.utcnow)
