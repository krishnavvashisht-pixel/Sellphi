from dataclasses import dataclass
from uuid import UUID

from app.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class MissionCreated(DomainEvent):
    """Emitted when a new mission is successfully created (always in DRAFT status)."""

    @classmethod
    def create(cls, mission_id: UUID, product_id: UUID, name: str) -> "MissionCreated":
        return cls(
            payload={
                "mission_id": str(mission_id),
                "product_id": str(product_id),
                "name": name,
            }
        )


@dataclass(frozen=True, slots=True)
class MissionUpdated(DomainEvent):
    """Emitted when a mission's fields are updated (excludes status transitions)."""

    @classmethod
    def create(cls, mission_id: UUID, product_id: UUID, updated_fields: list[str]) -> "MissionUpdated":
        return cls(
            payload={
                "mission_id": str(mission_id),
                "product_id": str(product_id),
                "updated_fields": updated_fields,
            }
        )


@dataclass(frozen=True, slots=True)
class MissionStarted(DomainEvent):
    """Emitted when a mission is run for the first time (DRAFT -> ACTIVE)."""

    @classmethod
    def create(cls, mission_id: UUID, product_id: UUID) -> "MissionStarted":
        return cls(
            payload={
                "mission_id": str(mission_id),
                "product_id": str(product_id),
            }
        )


@dataclass(frozen=True, slots=True)
class MissionPaused(DomainEvent):
    """Emitted when a mission is paused (ACTIVE -> PAUSED)."""

    @classmethod
    def create(cls, mission_id: UUID, product_id: UUID) -> "MissionPaused":
        return cls(
            payload={
                "mission_id": str(mission_id),
                "product_id": str(product_id),
            }
        )


@dataclass(frozen=True, slots=True)
class MissionResumed(DomainEvent):
    """Emitted when a paused mission resumes (PAUSED -> ACTIVE)."""

    @classmethod
    def create(cls, mission_id: UUID, product_id: UUID) -> "MissionResumed":
        return cls(
            payload={
                "mission_id": str(mission_id),
                "product_id": str(product_id),
            }
        )


@dataclass(frozen=True, slots=True)
class MissionCompleted(DomainEvent):
    """Emitted when a mission is marked complete (ACTIVE|PAUSED -> COMPLETED)."""

    @classmethod
    def create(cls, mission_id: UUID, product_id: UUID) -> "MissionCompleted":
        return cls(
            payload={
                "mission_id": str(mission_id),
                "product_id": str(product_id),
            }
        )


@dataclass(frozen=True, slots=True)
class MissionArchived(DomainEvent):
    """Emitted when a mission is archived (DRAFT|PAUSED|COMPLETED -> ARCHIVED)."""

    @classmethod
    def create(cls, mission_id: UUID, product_id: UUID) -> "MissionArchived":
        return cls(
            payload={
                "mission_id": str(mission_id),
                "product_id": str(product_id),
            }
        )


@dataclass(frozen=True, slots=True)
class MissionDeleted(DomainEvent):
    """Emitted when a mission is soft-deleted."""

    @classmethod
    def create(cls, mission_id: UUID, product_id: UUID) -> "MissionDeleted":
        return cls(
            payload={
                "mission_id": str(mission_id),
                "product_id": str(product_id),
            }
        )
