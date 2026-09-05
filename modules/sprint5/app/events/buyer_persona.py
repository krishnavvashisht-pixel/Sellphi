from dataclasses import dataclass
from uuid import UUID

from app.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class BuyerPersonaCreated(DomainEvent):
    """Emitted when a new buyer persona is successfully created."""

    @classmethod
    def create(
        cls, persona_id: UUID, product_id: UUID, name: str, is_default: bool
    ) -> "BuyerPersonaCreated":
        return cls(
            payload={
                "persona_id": str(persona_id),
                "product_id": str(product_id),
                "name": name,
                "is_default": is_default,
            }
        )


@dataclass(frozen=True, slots=True)
class BuyerPersonaUpdated(DomainEvent):
    """Emitted when a buyer persona is updated."""

    @classmethod
    def create(
        cls, persona_id: UUID, product_id: UUID, updated_fields: list[str]
    ) -> "BuyerPersonaUpdated":
        return cls(
            payload={
                "persona_id": str(persona_id),
                "product_id": str(product_id),
                "updated_fields": updated_fields,
            }
        )


@dataclass(frozen=True, slots=True)
class BuyerPersonaDeleted(DomainEvent):
    """Emitted when a buyer persona is soft-deleted."""

    @classmethod
    def create(cls, persona_id: UUID, product_id: UUID) -> "BuyerPersonaDeleted":
        return cls(
            payload={
                "persona_id": str(persona_id),
                "product_id": str(product_id),
            }
        )


@dataclass(frozen=True, slots=True)
class BuyerPersonaDefaultChanged(DomainEvent):
    """Emitted when a new buyer persona becomes the default for a product."""

    @classmethod
    def create(
        cls,
        product_id: UUID,
        new_default_persona_id: UUID,
        previous_default_persona_id: UUID | None,
    ) -> "BuyerPersonaDefaultChanged":
        return cls(
            payload={
                "product_id": str(product_id),
                "new_default_persona_id": str(new_default_persona_id),
                "previous_default_persona_id": (
                    str(previous_default_persona_id)
                    if previous_default_persona_id is not None
                    else None
                ),
            }
        )
