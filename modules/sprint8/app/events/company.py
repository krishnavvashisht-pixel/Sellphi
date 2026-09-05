from dataclasses import dataclass
from uuid import UUID

from app.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class CompanyCreated(DomainEvent):
    @classmethod
    def create(cls, company_id: UUID, workspace_id: UUID, name: str) -> "CompanyCreated":
        return cls(
            payload={
                "company_id": str(company_id),
                "workspace_id": str(workspace_id),
                "name": name,
            }
        )


@dataclass(frozen=True, slots=True)
class CompanyUpdated(DomainEvent):
    @classmethod
    def create(cls, company_id: UUID, workspace_id: UUID, updated_fields: list[str]) -> "CompanyUpdated":
        return cls(
            payload={
                "company_id": str(company_id),
                "workspace_id": str(workspace_id),
                "updated_fields": updated_fields,
            }
        )


@dataclass(frozen=True, slots=True)
class CompanyArchived(DomainEvent):
    @classmethod
    def create(cls, company_id: UUID, workspace_id: UUID) -> "CompanyArchived":
        return cls(
            payload={
                "company_id": str(company_id),
                "workspace_id": str(workspace_id),
            }
        )


@dataclass(frozen=True, slots=True)
class CompanyRestored(DomainEvent):
    @classmethod
    def create(cls, company_id: UUID, workspace_id: UUID) -> "CompanyRestored":
        return cls(
            payload={
                "company_id": str(company_id),
                "workspace_id": str(workspace_id),
            }
        )


@dataclass(frozen=True, slots=True)
class CompanyDeleted(DomainEvent):
    @classmethod
    def create(cls, company_id: UUID, workspace_id: UUID) -> "CompanyDeleted":
        return cls(
            payload={
                "company_id": str(company_id),
                "workspace_id": str(workspace_id),
            }
        )


@dataclass(frozen=True, slots=True)
class CompanyQualified(DomainEvent):
    @classmethod
    def create(cls, company_id: UUID, workspace_id: UUID) -> "CompanyQualified":
        return cls(
            payload={
                "company_id": str(company_id),
                "workspace_id": str(workspace_id),
            }
        )


@dataclass(frozen=True, slots=True)
class CompanyScored(DomainEvent):
    """Emitted whenever one or more of the company's scores changes."""

    @classmethod
    def create(
        cls,
        company_id: UUID,
        workspace_id: UUID,
        health_score: int | None,
        fit_score: int | None,
        engagement_score: int | None,
        confidence_score: int | None,
    ) -> "CompanyScored":
        return cls(
            payload={
                "company_id": str(company_id),
                "workspace_id": str(workspace_id),
                "health_score": health_score,
                "fit_score": fit_score,
                "engagement_score": engagement_score,
                "confidence_score": confidence_score,
            }
        )
