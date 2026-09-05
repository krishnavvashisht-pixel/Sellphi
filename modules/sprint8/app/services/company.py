import re
from typing import Any
from uuid import UUID

from app.core.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
)
from app.events.company import (
    CompanyArchived,
    CompanyCreated,
    CompanyDeleted,
    CompanyQualified,
    CompanyRestored,
    CompanyScored,
    CompanyUpdated,
)
from app.models.company import Company, CompanyStatus, FundingStage
from app.repositories.company import CompanyRepository
from app.repositories.mission import MissionRepository
from app.repositories.product import ProductRepository
from app.repositories.workspace import WorkspaceRepository
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.utils.time import utc_now


# ── Domain exceptions ─────────────────────────────────────────────────────────

class CompanyNotFoundError(EntityNotFoundError):
    error_code = "company_not_found"


class CompanyWorkspaceNotFoundError(EntityNotFoundError):
    error_code = "company_workspace_not_found"


class CompanyMissionNotFoundError(EntityNotFoundError):
    error_code = "company_mission_not_found"


class CompanyDuplicateDomainError(BusinessRuleViolationError):
    error_code = "company_duplicate_domain"


class CompanyBusinessRuleError(BusinessRuleViolationError):
    error_code = "company_business_rule_violation"


class CompanyInvalidTransitionError(BusinessRuleViolationError):
    error_code = "company_invalid_status_transition"


_SCORE_FIELDS = ("health_score", "fit_score", "engagement_score", "confidence_score")

_SCHEME_RE = re.compile(r"^[a-z]+://")
_WWW_RE = re.compile(r"^www\.")


def _normalize_domain(raw: str) -> str:
    value = raw.strip().lower()
    value = _SCHEME_RE.sub("", value)
    value = _WWW_RE.sub("", value)
    value = value.split("/")[0]
    value = value.split("?")[0]
    value = value.split(":")[0]
    return value


def _normalize_web_presence(website: str | None, domain: str | None) -> tuple[str | None, str | None]:
    """
    Derives a canonical (website, domain) pair from whatever the caller supplied.
    `website` wins if both are given and disagree — the domain is always
    re-derived from whichever source string is used, so the two can never
    drift apart in storage.
    """
    source = website or domain
    if not source:
        return None, None
    normalized_domain = _normalize_domain(source)
    normalized_website = f"https://{normalized_domain}"
    return normalized_website, normalized_domain


# ── Service ───────────────────────────────────────────────────────────────────

class CompanyService:
    def __init__(
        self,
        company_repository: CompanyRepository,
        workspace_repository: WorkspaceRepository,
        mission_repository: MissionRepository,
        product_repository: ProductRepository,
    ) -> None:
        self._company_repository = company_repository
        self._workspace_repository = workspace_repository
        self._mission_repository = mission_repository
        self._product_repository = product_repository

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create(self, payload: CompanyCreate) -> Company:
        await self._ensure_workspace_exists(payload.workspace_id)

        website, domain = _normalize_web_presence(payload.website, payload.domain)
        if domain is not None:
            await self._ensure_domain_unique(domain, payload.workspace_id)

        if payload.mission_id is not None:
            await self._ensure_mission_belongs_to_workspace(payload.mission_id, payload.workspace_id)

        self._validate_scores(
            health_score=payload.health_score,
            fit_score=payload.fit_score,
            engagement_score=payload.engagement_score,
            confidence_score=payload.confidence_score,
        )

        company = Company(
            workspace_id=payload.workspace_id,
            mission_id=payload.mission_id,
            name=payload.name,
            legal_name=payload.legal_name,
            website=website,
            domain=domain,
            linkedin_url=payload.linkedin_url,
            industry=payload.industry,
            sub_industry=payload.sub_industry,
            company_size=payload.company_size,
            annual_revenue=payload.annual_revenue,
            headquarters_country=payload.headquarters_country,
            headquarters_state=payload.headquarters_state,
            headquarters_city=payload.headquarters_city,
            founded_year=payload.founded_year,
            company_type=payload.company_type,
            ownership_type=payload.ownership_type,
            stock_symbol=payload.stock_symbol,
            funding_stage=payload.funding_stage,
            technologies=payload.technologies,
            description=payload.description,
            summary=payload.summary,
            tags=payload.tags,
            metadata_=payload.metadata,
            health_score=payload.health_score,
            fit_score=payload.fit_score,
            engagement_score=payload.engagement_score,
            confidence_score=payload.confidence_score,
            status=CompanyStatus.NEW,
            source=payload.source,
            created_by=payload.created_by,
        )

        try:
            created = await self._company_repository.create(company)
            await self._company_repository.commit()
        except Exception:
            await self._company_repository.rollback()
            raise

        _emit(CompanyCreated.create(company_id=created.id, workspace_id=created.workspace_id, name=created.name))
        return created

    async def list(
        self,
        *,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        industry: str | None = None,
        status: CompanyStatus | None = None,
        funding_stage: FundingStage | None = None,
        company_size: str | None = None,
        country: str | None = None,
        mission_id: UUID | None = None,
    ) -> tuple[list[Company], int]:
        await self._ensure_workspace_exists(workspace_id)
        return await self._company_repository.list(
            workspace_id=workspace_id,
            offset=offset,
            limit=limit,
            search=search,
            industry=industry,
            status=status,
            funding_stage=funding_stage,
            company_size=company_size,
            country=country,
            mission_id=mission_id,
        )

    async def get(self, company_id: UUID, workspace_id: UUID | None = None) -> Company:
        company = await self._company_repository.get_by_id(company_id, workspace_id=workspace_id)
        if company is None:
            raise CompanyNotFoundError("Company not found")
        return company

    async def update(self, company_id: UUID, payload: CompanyUpdate) -> Company:
        company = await self.get(company_id)
        if company.status == CompanyStatus.ARCHIVED:
            raise CompanyBusinessRuleError("Cannot update an archived company. Restore it first.")

        updates = payload.model_dump(exclude_unset=True)

        if "website" in updates or "domain" in updates:
            new_website, new_domain = _normalize_web_presence(
                updates.get("website", company.website),
                updates.get("domain", company.domain),
            )
            if new_domain is not None and new_domain != company.domain:
                await self._ensure_domain_unique(new_domain, company.workspace_id, exclude_company_id=company.id)
            updates["website"] = new_website
            updates["domain"] = new_domain

        if "mission_id" in updates and updates["mission_id"] is not None:
            await self._ensure_mission_belongs_to_workspace(updates["mission_id"], company.workspace_id)

        self._validate_scores(
            health_score=updates.get("health_score", company.health_score),
            fit_score=updates.get("fit_score", company.fit_score),
            engagement_score=updates.get("engagement_score", company.engagement_score),
            confidence_score=updates.get("confidence_score", company.confidence_score),
        )

        _SIMPLE_FIELDS = {
            "mission_id", "name", "legal_name", "website", "domain", "linkedin_url",
            "industry", "sub_industry", "company_size", "annual_revenue",
            "headquarters_country", "headquarters_state", "headquarters_city", "founded_year",
            "company_type", "ownership_type", "stock_symbol", "funding_stage",
            "technologies", "description", "summary", "tags",
            "health_score", "fit_score", "engagement_score", "confidence_score",
        }
        score_fields_changed = any(field in updates for field in _SCORE_FIELDS)

        for field in _SIMPLE_FIELDS:
            if field in updates:
                setattr(company, field, updates[field])

        if "metadata" in updates:
            company.metadata_ = updates["metadata"]

        try:
            updated = await self._company_repository.update(company)
            await self._company_repository.commit()
        except Exception:
            await self._company_repository.rollback()
            raise

        _emit(CompanyUpdated.create(
            company_id=updated.id, workspace_id=updated.workspace_id, updated_fields=list(updates.keys()),
        ))
        if score_fields_changed:
            _emit(CompanyScored.create(
                company_id=updated.id,
                workspace_id=updated.workspace_id,
                health_score=updated.health_score,
                fit_score=updated.fit_score,
                engagement_score=updated.engagement_score,
                confidence_score=updated.confidence_score,
            ))

        return updated

    async def update_scores(
        self,
        company_id: UUID,
        *,
        health_score: int | None = None,
        fit_score: int | None = None,
        engagement_score: int | None = None,
        confidence_score: int | None = None,
    ) -> Company:
        """Convenience wrapper around update() for score-only changes."""
        fields: dict[str, Any] = {}
        if health_score is not None:
            fields["health_score"] = health_score
        if fit_score is not None:
            fields["fit_score"] = fit_score
        if engagement_score is not None:
            fields["engagement_score"] = engagement_score
        if confidence_score is not None:
            fields["confidence_score"] = confidence_score
        return await self.update(company_id, CompanyUpdate(**fields))

    # ── Status / lifecycle actions ──────────────────────────────────────────

    async def archive(self, company_id: UUID) -> Company:
        company = await self.get(company_id)
        if company.status == CompanyStatus.ARCHIVED:
            raise CompanyInvalidTransitionError("Company is already archived")

        company.status = CompanyStatus.ARCHIVED
        await self._persist(company)

        _emit(CompanyArchived.create(company_id=company.id, workspace_id=company.workspace_id))
        return company

    async def restore(self, company_id: UUID) -> Company:
        """
        Reverts an archived company to NEW. There is no dedicated
        "previous status" field, so restore intentionally resets to a neutral
        starting state rather than guessing what the prior status was —
        re-qualify explicitly via `qualify()` if needed.
        """
        company = await self.get(company_id)
        if company.status != CompanyStatus.ARCHIVED:
            raise CompanyInvalidTransitionError("Company is not archived")

        company.status = CompanyStatus.NEW
        await self._persist(company)

        _emit(CompanyRestored.create(company_id=company.id, workspace_id=company.workspace_id))
        return company

    async def qualify(self, company_id: UUID) -> Company:
        """
        Service-only capability (no REST route in this sprint's endpoint list).
        NEW|DISQUALIFIED -> QUALIFIED.
        """
        company = await self.get(company_id)
        if company.status == CompanyStatus.ARCHIVED:
            raise CompanyInvalidTransitionError("Cannot qualify an archived company. Restore it first.")
        if company.status == CompanyStatus.QUALIFIED:
            raise CompanyInvalidTransitionError("Company is already qualified")

        company.status = CompanyStatus.QUALIFIED
        await self._persist(company)

        _emit(CompanyQualified.create(company_id=company.id, workspace_id=company.workspace_id))
        return company

    async def delete(self, company_id: UUID) -> None:
        company = await self.get(company_id)
        company.deleted_at = utc_now()

        try:
            await self._company_repository.soft_delete(company)
            await self._company_repository.commit()
        except Exception:
            await self._company_repository.rollback()
            raise

        _emit(CompanyDeleted.create(company_id=company.id, workspace_id=company.workspace_id))

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _persist(self, company: Company) -> Company:
        try:
            updated = await self._company_repository.update(company)
            await self._company_repository.commit()
            return updated
        except Exception:
            await self._company_repository.rollback()
            raise

    async def _ensure_workspace_exists(self, workspace_id: UUID) -> None:
        workspace = await self._workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise CompanyWorkspaceNotFoundError("Workspace not found")

    async def _ensure_domain_unique(
        self, domain: str, workspace_id: UUID, exclude_company_id: UUID | None = None
    ) -> None:
        existing = await self._company_repository.get_by_domain(domain, workspace_id)
        if existing is not None and existing.id != exclude_company_id:
            raise CompanyDuplicateDomainError(
                f"A company with domain '{domain}' already exists in this workspace"
            )

    async def _ensure_mission_belongs_to_workspace(self, mission_id: UUID, workspace_id: UUID) -> None:
        # Mission has no workspace_id column — it belongs to a Product, which
        # belongs to a Workspace — so this is a two-hop lookup.
        mission = await self._mission_repository.get_by_id(mission_id)
        if mission is None:
            raise CompanyMissionNotFoundError("Mission not found")

        product = await self._product_repository.get_by_id(mission.product_id)
        if product is None or product.workspace_id != workspace_id:
            raise CompanyMissionNotFoundError("Mission does not belong to this workspace")

    def _validate_scores(
        self,
        *,
        health_score: int | None,
        fit_score: int | None,
        engagement_score: int | None,
        confidence_score: int | None,
    ) -> None:
        for field_name, value in (
            ("health_score", health_score),
            ("fit_score", fit_score),
            ("engagement_score", engagement_score),
            ("confidence_score", confidence_score),
        ):
            if value is not None and not (0 <= value <= 100):
                raise CompanyBusinessRuleError(f"{field_name} must be between 0 and 100")


def _emit(event: object) -> None:
    """
    Fire-and-forget event emission.
    In production wire up an EventBus here (Redis Streams, Kafka, etc.).
    """
    # TODO: inject EventBus and call await event_bus.publish(event)
    pass
