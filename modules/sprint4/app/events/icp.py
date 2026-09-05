from dataclasses import dataclass
from uuid import UUID

from app.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class ICPCreated(DomainEvent):
    """Emitted when a new ICP is successfully created."""

    @classmethod
    def create(cls, icp_id: UUID, product_id: UUID, name: str, is_default: bool) -> "ICPCreated":
        return cls(
            payload={
                "icp_id": str(icp_id),
                "product_id": str(product_id),
                "name": name,
                "is_default": is_default,
            }
        )


@dataclass(frozen=True, slots=True)
class ICPUpdated(DomainEvent):
    """Emitted when an ICP is updated."""

    @classmethod
    def create(cls, icp_id: UUID, product_id: UUID, updated_fields: list[str]) -> "ICPUpdated":
        return cls(
            payload={
                "icp_id": str(icp_id),
                "product_id": str(product_id),
                "updated_fields": updated_fields,
            }
        )


@dataclass(frozen=True, slots=True)
class ICPDeleted(DomainEvent):
    """Emitted when an ICP is soft-deleted."""

    @classmethod
    def create(cls, icp_id: UUID, product_id: UUID) -> "ICPDeleted":
        return cls(
            payload={
                "icp_id": str(icp_id),
                "product_id": str(product_id),
            }
        )


@dataclass(frozen=True, slots=True)
class ICPDefaultChanged(DomainEvent):
    """Emitted when a new ICP becomes the default for a product."""

    @classmethod
    def create(
        cls,
        product_id: UUID,
        new_default_icp_id: UUID,
        previous_default_icp_id: UUID | None,
    ) -> "ICPDefaultChanged":
        return cls(
            payload={
                "product_id": str(product_id),
                "new_default_icp_id": str(new_default_icp_id),
                "previous_default_icp_id": (
                    str(previous_default_icp_id)
                    if previous_default_icp_id is not None
                    else None
                ),
            }
        )
