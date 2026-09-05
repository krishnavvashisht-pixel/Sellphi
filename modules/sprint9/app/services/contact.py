import re
from typing import Any
from uuid import UUID

from app.core.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
)
from app.events.contact import (
    ContactArchived,
    ContactCreated,
    ContactDeleted,
    ContactRestored,
    ContactScored,
    ContactUpdated,
    ContactVerified,
    RelationshipStatusChanged,
)
from app.models.buyer_persona import SeniorityLevel
from app.models.contact import Contact, ContactStatus, PreferredChannel, RelationshipStatus
from app.repositories.buyer_persona import BuyerPersonaRepository
from app.repositories.company import CompanyRepository
from app.repositories.contact import ContactRepository
from app.repositories.product import ProductRepository
from app.schemas.contact import ContactCreate, ContactUpdate
from app.utils.time import utc_now


# ── Domain exceptions ─────────────────────────────────────────────────────────

class ContactNotFoundError(EntityNotFoundError):
    error_code = "contact_not_found"


class ContactCompanyNotFoundError(EntityNotFoundError):
    error_code = "contact_company_not_found"


class ContactBuyerPersonaNotFoundError(EntityNotFoundError):
    error_code = "contact_buyer_persona_not_found"


class ContactDuplicateEmailError(BusinessRuleViolationError):
    error_code = "contact_duplicate_email"


class ContactDuplicateLinkedInError(BusinessRuleViolationError):
    error_code = "contact_duplicate_linkedin"


class ContactBusinessRuleError(BusinessRuleViolationError):
    error_code = "contact_business_rule_violation"


class ContactInvalidTransitionError(BusinessRuleViolationError):
    error_code = "contact_invalid_status_transition"


_SCORE_FIELDS = ("influence_score", "engagement_score", "confidence_score")

_SCHEME_RE = re.compile(r"^[a-zA-Z]+://")
_WWW_RE = re.compile(r"^www\.", re.IGNORECASE)


def _normalize_email(raw: str) -> str:
    return raw.strip().lower()


def _normalize_linkedin_url(raw: str) -> str:
    """Lowercases the host (LinkedIn URLs aren't case-sensitive there) but
    preserves path casing (profile slugs sometimes are), strips scheme/www/
    query string/trailing slash, and re-adds a canonical https:// scheme."""
    value = raw.strip()
    value = _SCHEME_RE.sub("", value)
    value = _WWW_RE.sub("", value)
    parts = value.split("/", 1)
    host = parts[0].lower()
    path = "/" + parts[1] if len(parts) > 1 else ""
    path = path.split("?")[0].rstrip("/")
    return f"https://{host}{path}"


def _default_full_name(first_name: str, last_name: str) -> str:
    return f"{first_name} {last_name}".strip()


# ── Service ───────────────────────────────────────────────────────────────────

class ContactService:
    def __init__(
        self,
        contact_repository: ContactRepository,
        company_repository: CompanyRepository,
        buyer_persona_repository: BuyerPersonaRepository,
        product_repository: ProductRepository,
    ) -> None:
        self._contact_repository = contact_repository
        self._company_repository = company_repository
        self._buyer_persona_repository = buyer_persona_repository
        self._product_repository = product_repository

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create(self, payload: ContactCreate) -> Contact:
        company = await self._get_company_or_raise(payload.company_id)

        if payload.buyer_persona_id is not None:
            await self._ensure_buyer_persona_in_workspace(payload.buyer_persona_id, company.workspace_id)

        email = _normalize_email(payload.email) if payload.email else None
        if email is not None:
            await self._ensure_email_unique(email, payload.company_id)

        alternate_emails = [_normalize_email(e) for e in payload.alternate_emails]

        linkedin_url = _normalize_linkedin_url(payload.linkedin_url) if payload.linkedin_url else None
        if linkedin_url is not None:
            await self._ensure_linkedin_unique(linkedin_url, payload.company_id)

        self._validate_scores(
            influence_score=payload.influence_score,
            engagement_score=payload.engagement_score,
            confidence_score=payload.confidence_score,
        )

        full_name = payload.full_name or _default_full_name(payload.first_name, payload.last_name)

        contact = Contact(
            company_id=payload.company_id,
            buyer_persona_id=payload.buyer_persona_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            full_name=full_name,
            preferred_name=payload.preferred_name,
            job_title=payload.job_title,
            department=payload.department,
            seniority=payload.seniority,
            buying_role=payload.buying_role,
            email=email,
            alternate_emails=alternate_emails,
            phone=payload.phone,
            mobile=payload.mobile,
            linkedin_url=linkedin_url,
            twitter_url=payload.twitter_url,
            location_country=payload.location_country,
            location_state=payload.location_state,
            location_city=payload.location_city,
            timezone=payload.timezone,
            languages=payload.languages,
            skills=payload.skills,
            interests=payload.interests,
            influence_score=payload.influence_score,
            engagement_score=payload.engagement_score,
            confidence_score=payload.confidence_score,
            relationship_status=payload.relationship_status,
            preferred_channel=payload.preferred_channel,
            last_contacted_at=payload.last_contacted_at,
            last_replied_at=payload.last_replied_at,
            notes=payload.notes,
            metadata_=payload.metadata,
            status=ContactStatus.NEW,
            source=payload.source,
            created_by=payload.created_by,
        )

        try:
            created = await self._contact_repository.create(contact)
            await self._contact_repository.commit()
        except Exception:
            await self._contact_repository.rollback()
            raise

        _emit(ContactCreated.create(
            contact_id=created.id, company_id=created.company_id, full_name=created.full_name,
        ))
        return created

    async def list(
        self,
        *,
        company_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        department: str | None = None,
        seniority: SeniorityLevel | None = None,
        relationship_status: RelationshipStatus | None = None,
        preferred_channel: PreferredChannel | None = None,
        status: ContactStatus | None = None,
    ) -> tuple[list[Contact], int]:
        await self._get_company_or_raise(company_id)
        return await self._contact_repository.list(
            company_id=company_id,
            offset=offset,
            limit=limit,
            search=search,
            department=department,
            seniority=seniority,
            relationship_status=relationship_status,
            preferred_channel=preferred_channel,
            status=status,
        )

    async def get(self, contact_id: UUID, company_id: UUID | None = None) -> Contact:
        contact = await self._contact_repository.get_by_id(contact_id, company_id=company_id)
        if contact is None:
            raise ContactNotFoundError("Contact not found")
        return contact

    async def update(self, contact_id: UUID, payload: ContactUpdate) -> Contact:
        contact = await self.get(contact_id)
        if contact.status == ContactStatus.ARCHIVED:
            raise ContactBusinessRuleError("Cannot update an archived contact. Restore it first.")

        updates = payload.model_dump(exclude_unset=True)

        if "buyer_persona_id" in updates and updates["buyer_persona_id"] is not None:
            company = await self._get_company_or_raise(contact.company_id)
            await self._ensure_buyer_persona_in_workspace(updates["buyer_persona_id"], company.workspace_id)

        if "email" in updates and updates["email"] is not None:
            new_email = _normalize_email(updates["email"])
            if new_email != contact.email:
                await self._ensure_email_unique(new_email, contact.company_id, exclude_contact_id=contact.id)
            updates["email"] = new_email

        if "alternate_emails" in updates and updates["alternate_emails"] is not None:
            updates["alternate_emails"] = [_normalize_email(e) for e in updates["alternate_emails"]]

        if "linkedin_url" in updates and updates["linkedin_url"] is not None:
            new_linkedin_url = _normalize_linkedin_url(updates["linkedin_url"])
            if new_linkedin_url != contact.linkedin_url:
                await self._ensure_linkedin_unique(
                    new_linkedin_url, contact.company_id, exclude_contact_id=contact.id
                )
            updates["linkedin_url"] = new_linkedin_url

        self._validate_scores(
            influence_score=updates.get("influence_score", contact.influence_score),
            engagement_score=updates.get("engagement_score", contact.engagement_score),
            confidence_score=updates.get("confidence_score", contact.confidence_score),
        )

        # Auto-recompute full_name if first/last changed but full_name wasn't
        # explicitly supplied in this same update.
        if ("first_name" in updates or "last_name" in updates) and "full_name" not in updates:
            updates["full_name"] = _default_full_name(
                updates.get("first_name", contact.first_name),
                updates.get("last_name", contact.last_name),
            )

        previous_relationship_status = contact.relationship_status
        score_fields_changed = any(field in updates for field in _SCORE_FIELDS)

        _SIMPLE_FIELDS = {
            "buyer_persona_id", "first_name", "last_name", "full_name", "preferred_name",
            "job_title", "department", "seniority", "buying_role",
            "email", "alternate_emails", "phone", "mobile", "linkedin_url", "twitter_url",
            "location_country", "location_state", "location_city", "timezone",
            "languages", "skills", "interests",
            "influence_score", "engagement_score", "confidence_score",
            "relationship_status", "preferred_channel",
            "last_contacted_at", "last_replied_at", "notes",
        }
        for field in _SIMPLE_FIELDS:
            if field in updates:
                setattr(contact, field, updates[field])

        if "metadata" in updates:
            contact.metadata_ = updates["metadata"]

        try:
            updated = await self._contact_repository.update(contact)
            await self._contact_repository.commit()
        except Exception:
            await self._contact_repository.rollback()
            raise

        _emit(ContactUpdated.create(
            contact_id=updated.id, company_id=updated.company_id, updated_fields=list(updates.keys()),
        ))
        if score_fields_changed:
            _emit(ContactScored.create(
                contact_id=updated.id,
                company_id=updated.company_id,
                influence_score=updated.influence_score,
                engagement_score=updated.engagement_score,
                confidence_score=updated.confidence_score,
            ))
        if "relationship_status" in updates and updated.relationship_status != previous_relationship_status:
            _emit(RelationshipStatusChanged.create(
                contact_id=updated.id,
                company_id=updated.company_id,
                previous_status=previous_relationship_status.value,
                new_status=updated.relationship_status.value,
            ))

        return updated

    async def update_scores(
        self,
        contact_id: UUID,
        *,
        influence_score: int | None = None,
        engagement_score: int | None = None,
        confidence_score: int | None = None,
    ) -> Contact:
        """Convenience wrapper around update() for score-only changes."""
        fields: dict[str, Any] = {}
        if influence_score is not None:
            fields["influence_score"] = influence_score
        if engagement_score is not None:
            fields["engagement_score"] = engagement_score
        if confidence_score is not None:
            fields["confidence_score"] = confidence_score
        return await self.update(contact_id, ContactUpdate(**fields))

    # ── Status / lifecycle actions ──────────────────────────────────────────

    async def archive(self, contact_id: UUID) -> Contact:
        contact = await self.get(contact_id)
        if contact.status == ContactStatus.ARCHIVED:
            raise ContactInvalidTransitionError("Contact is already archived")

        contact.status = ContactStatus.ARCHIVED
        await self._persist(contact)

        _emit(ContactArchived.create(contact_id=contact.id, company_id=contact.company_id))
        return contact

    async def restore(self, contact_id: UUID) -> Contact:
        """
        Reverts an archived contact to NEW. There is no dedicated "previous
        status" field, so restore intentionally resets to a neutral starting
        state rather than guessing — re-verify explicitly via `verify()` if
        needed.
        """
        contact = await self.get(contact_id)
        if contact.status != ContactStatus.ARCHIVED:
            raise ContactInvalidTransitionError("Contact is not archived")

        contact.status = ContactStatus.NEW
        await self._persist(contact)

        _emit(ContactRestored.create(contact_id=contact.id, company_id=contact.company_id))
        return contact

    async def verify(self, contact_id: UUID) -> Contact:
        """
        Service-only capability (no REST route in this sprint's endpoint list).
        NEW -> VERIFIED, e.g. after a future email-verification workflow confirms
        deliverability.
        """
        contact = await self.get(contact_id)
        if contact.status == ContactStatus.ARCHIVED:
            raise ContactInvalidTransitionError("Cannot verify an archived contact. Restore it first.")
        if contact.status == ContactStatus.VERIFIED:
            raise ContactInvalidTransitionError("Contact is already verified")

        contact.status = ContactStatus.VERIFIED
        await self._persist(contact)

        _emit(ContactVerified.create(contact_id=contact.id, company_id=contact.company_id))
        return contact

    async def delete(self, contact_id: UUID) -> None:
        contact = await self.get(contact_id)
        contact.deleted_at = utc_now()

        try:
            await self._contact_repository.soft_delete(contact)
            await self._contact_repository.commit()
        except Exception:
            await self._contact_repository.rollback()
            raise

        _emit(ContactDeleted.create(contact_id=contact.id, company_id=contact.company_id))

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _persist(self, contact: Contact) -> Contact:
        try:
            updated = await self._contact_repository.update(contact)
            await self._contact_repository.commit()
            return updated
        except Exception:
            await self._contact_repository.rollback()
            raise

    async def _get_company_or_raise(self, company_id: UUID):  # noqa: ANN201
        company = await self._company_repository.get_by_id(company_id)
        if company is None:
            raise ContactCompanyNotFoundError("Company not found")
        return company

    async def _ensure_email_unique(
        self, email: str, company_id: UUID, exclude_contact_id: UUID | None = None
    ) -> None:
        existing = await self._contact_repository.find_by_email(email, company_id)
        if existing is not None and existing.id != exclude_contact_id:
            raise ContactDuplicateEmailError(
                f"A contact with email '{email}' already exists in this company"
            )

    async def _ensure_linkedin_unique(
        self, linkedin_url: str, company_id: UUID, exclude_contact_id: UUID | None = None
    ) -> None:
        """
        Business-rule-level duplicate prevention (not DB-enforced — your spec
        only calls out email as a hard-unique field). Prevents two contact
        records in the same company from pointing at the same LinkedIn profile.
        """
        existing = await self._contact_repository.find_by_linkedin(linkedin_url, company_id)
        if existing is not None and existing.id != exclude_contact_id:
            raise ContactDuplicateLinkedInError(
                f"A contact with LinkedIn profile '{linkedin_url}' already exists in this company"
            )

    async def _ensure_buyer_persona_in_workspace(self, buyer_persona_id: UUID, workspace_id: UUID) -> None:
        # BuyerPersona has no workspace_id column — it belongs to a Product,
        # which belongs to a Workspace — so this is a two-hop lookup, same
        # pattern as CompanyService._ensure_mission_belongs_to_workspace.
        persona = await self._buyer_persona_repository.get_by_id(buyer_persona_id)
        if persona is None:
            raise ContactBuyerPersonaNotFoundError("Buyer persona not found")

        product = await self._product_repository.get_by_id(persona.product_id)
        if product is None or product.workspace_id != workspace_id:
            raise ContactBuyerPersonaNotFoundError("Buyer persona does not belong to this workspace")

    def _validate_scores(
        self,
        *,
        influence_score: int | None,
        engagement_score: int | None,
        confidence_score: int | None,
    ) -> None:
        for field_name, value in (
            ("influence_score", influence_score),
            ("engagement_score", engagement_score),
            ("confidence_score", confidence_score),
        ):
            if value is not None and not (0 <= value <= 100):
                raise ContactBusinessRuleError(f"{field_name} must be between 0 and 100")


def _emit(event: object) -> None:
    """
    Fire-and-forget event emission.
    In production wire up an EventBus here (Redis Streams, Kafka, etc.).
    """
    # TODO: inject EventBus and call await event_bus.publish(event)
    pass
