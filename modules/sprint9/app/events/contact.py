from dataclasses import dataclass
from uuid import UUID

from app.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class ContactCreated(DomainEvent):
    @classmethod
    def create(cls, contact_id: UUID, company_id: UUID, full_name: str) -> "ContactCreated":
        return cls(
            payload={
                "contact_id": str(contact_id),
                "company_id": str(company_id),
                "full_name": full_name,
            }
        )


@dataclass(frozen=True, slots=True)
class ContactUpdated(DomainEvent):
    @classmethod
    def create(cls, contact_id: UUID, company_id: UUID, updated_fields: list[str]) -> "ContactUpdated":
        return cls(
            payload={
                "contact_id": str(contact_id),
                "company_id": str(company_id),
                "updated_fields": updated_fields,
            }
        )


@dataclass(frozen=True, slots=True)
class ContactArchived(DomainEvent):
    @classmethod
    def create(cls, contact_id: UUID, company_id: UUID) -> "ContactArchived":
        return cls(payload={"contact_id": str(contact_id), "company_id": str(company_id)})


@dataclass(frozen=True, slots=True)
class ContactRestored(DomainEvent):
    @classmethod
    def create(cls, contact_id: UUID, company_id: UUID) -> "ContactRestored":
        return cls(payload={"contact_id": str(contact_id), "company_id": str(company_id)})


@dataclass(frozen=True, slots=True)
class ContactDeleted(DomainEvent):
    @classmethod
    def create(cls, contact_id: UUID, company_id: UUID) -> "ContactDeleted":
        return cls(payload={"contact_id": str(contact_id), "company_id": str(company_id)})


@dataclass(frozen=True, slots=True)
class ContactVerified(DomainEvent):
    """Emitted when a contact's status moves NEW -> VERIFIED."""

    @classmethod
    def create(cls, contact_id: UUID, company_id: UUID) -> "ContactVerified":
        return cls(payload={"contact_id": str(contact_id), "company_id": str(company_id)})


@dataclass(frozen=True, slots=True)
class ContactScored(DomainEvent):
    """Emitted whenever one or more of the contact's scores changes."""

    @classmethod
    def create(
        cls,
        contact_id: UUID,
        company_id: UUID,
        influence_score: int | None,
        engagement_score: int | None,
        confidence_score: int | None,
    ) -> "ContactScored":
        return cls(
            payload={
                "contact_id": str(contact_id),
                "company_id": str(company_id),
                "influence_score": influence_score,
                "engagement_score": engagement_score,
                "confidence_score": confidence_score,
            }
        )


@dataclass(frozen=True, slots=True)
class RelationshipStatusChanged(DomainEvent):
    @classmethod
    def create(
        cls, contact_id: UUID, company_id: UUID, previous_status: str, new_status: str
    ) -> "RelationshipStatusChanged":
        return cls(
            payload={
                "contact_id": str(contact_id),
                "company_id": str(company_id),
                "previous_status": previous_status,
                "new_status": new_status,
            }
        )
