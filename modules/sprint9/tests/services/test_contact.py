from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.models.buyer_persona import BuyerPersona, PersonaStatus, SeniorityLevel
from app.models.company import Company, CompanyStatus
from app.models.contact import Contact, ContactStatus, RelationshipStatus
from app.models.product import Product, ProductStatus
from app.schemas.contact import ContactCreate, ContactUpdate
from app.services.contact import (
    ContactBusinessRuleError,
    ContactBuyerPersonaNotFoundError,
    ContactCompanyNotFoundError,
    ContactDuplicateEmailError,
    ContactDuplicateLinkedInError,
    ContactInvalidTransitionError,
    ContactNotFoundError,
    ContactService,
)


# ── Fake repositories ─────────────────────────────────────────────────────────

class FakeContactRepository:
    def __init__(self, contacts: list[Contact] | None = None) -> None:
        self.contacts = contacts or []
        self.commits = 0
        self.rollbacks = 0

    async def create(self, contact: Contact) -> Contact:
        self._hydrate(contact)
        self.contacts.append(contact)
        return contact

    async def list(
        self,
        *,
        company_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        department: str | None = None,
        seniority: object | None = None,
        relationship_status: RelationshipStatus | None = None,
        preferred_channel: object | None = None,
        status: ContactStatus | None = None,
    ) -> tuple[list[Contact], int]:
        filtered = [
            c for c in self.contacts
            if c.company_id == company_id and c.deleted_at is None
        ]
        if status is not None:
            filtered = [c for c in filtered if c.status == status]
        if department is not None:
            filtered = [c for c in filtered if c.department == department]
        if seniority is not None:
            filtered = [c for c in filtered if c.seniority == seniority]
        if relationship_status is not None:
            filtered = [c for c in filtered if c.relationship_status == relationship_status]
        if search:
            q = search.lower()
            filtered = [c for c in filtered if q in c.full_name.lower()]
        return filtered[offset: offset + limit], len(filtered)

    async def get_by_id(self, contact_id: UUID, company_id: UUID | None = None) -> Contact | None:
        return next(
            (
                c for c in self.contacts
                if c.id == contact_id
                and c.deleted_at is None
                and (company_id is None or c.company_id == company_id)
            ),
            None,
        )

    async def find_by_email(self, email: str, company_id: UUID) -> Contact | None:
        return next(
            (
                c for c in self.contacts
                if c.company_id == company_id and c.email == email and c.deleted_at is None
            ),
            None,
        )

    async def find_by_linkedin(self, linkedin_url: str, company_id: UUID) -> Contact | None:
        return next(
            (
                c for c in self.contacts
                if c.company_id == company_id and c.linkedin_url == linkedin_url and c.deleted_at is None
            ),
            None,
        )

    async def update(self, contact: Contact) -> Contact:
        contact.updated_at = datetime.now(UTC)
        return contact

    async def soft_delete(self, contact: Contact) -> Contact:
        return contact

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    def _hydrate(self, contact: Contact) -> None:
        now = datetime.now(UTC)
        contact.id = uuid4()
        contact.created_at = now
        contact.updated_at = now
        contact.deleted_at = None
        contact.is_deleted = False


class FakeCompanyRepository:
    def __init__(self) -> None:
        self.companies: dict[UUID, UUID] = {}  # company_id -> workspace_id

    def register(self, company_id: UUID, workspace_id: UUID) -> None:
        self.companies[company_id] = workspace_id

    async def get_by_id(self, company_id: UUID, workspace_id: UUID | None = None) -> Company | None:
        owning_workspace_id = self.companies.get(company_id)
        if owning_workspace_id is None:
            return None
        now = datetime.now(UTC)
        company = Company(
            workspace_id=owning_workspace_id, name="Test Company", status=CompanyStatus.NEW
        )
        company.id = company_id
        company.created_at = now
        company.updated_at = now
        company.deleted_at = None
        company.is_deleted = False
        return company


class FakeBuyerPersonaRepository:
    def __init__(self) -> None:
        self.personas: dict[UUID, UUID] = {}  # persona_id -> product_id

    def register(self, persona_id: UUID, product_id: UUID) -> None:
        self.personas[persona_id] = product_id

    async def get_by_id(self, persona_id: UUID, product_id: UUID | None = None) -> BuyerPersona | None:
        owning_product_id = self.personas.get(persona_id)
        if owning_product_id is None:
            return None
        now = datetime.now(UTC)
        persona = BuyerPersona(product_id=owning_product_id, name="Test Persona", status=PersonaStatus.ACTIVE)
        persona.id = persona_id
        persona.created_at = now
        persona.updated_at = now
        persona.deleted_at = None
        persona.is_deleted = False
        return persona


class FakeProductRepository:
    def __init__(self) -> None:
        self.products: dict[UUID, UUID] = {}  # product_id -> workspace_id

    def register(self, product_id: UUID, workspace_id: UUID) -> None:
        self.products[product_id] = workspace_id

    async def get_by_id(self, product_id: UUID, workspace_id: UUID | None = None) -> Product | None:
        owning_workspace_id = self.products.get(product_id)
        if owning_workspace_id is None:
            return None
        now = datetime.now(UTC)
        product = Product(
            workspace_id=owning_workspace_id,
            name="Test Product",
            slug="test-product",
            status=ProductStatus.ACTIVE,
            settings={},
        )
        product.id = product_id
        product.created_at = now
        product.updated_at = now
        product.deleted_at = None
        product.is_deleted = False
        return product


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def workspace_id() -> UUID:
    return uuid4()


@pytest.fixture
def other_workspace_id() -> UUID:
    return uuid4()


@pytest.fixture
def company_repo() -> FakeCompanyRepository:
    return FakeCompanyRepository()


@pytest.fixture
def buyer_persona_repo() -> FakeBuyerPersonaRepository:
    return FakeBuyerPersonaRepository()


@pytest.fixture
def product_repo() -> FakeProductRepository:
    return FakeProductRepository()


@pytest.fixture
def contact_repo() -> FakeContactRepository:
    return FakeContactRepository()


@pytest.fixture
def company_id(company_repo: FakeCompanyRepository, workspace_id: UUID) -> UUID:
    cid = uuid4()
    company_repo.register(cid, workspace_id)
    return cid


@pytest.fixture
def other_company_id(company_repo: FakeCompanyRepository, other_workspace_id: UUID) -> UUID:
    cid = uuid4()
    company_repo.register(cid, other_workspace_id)
    return cid


@pytest.fixture
def service(
    contact_repo: FakeContactRepository,
    company_repo: FakeCompanyRepository,
    buyer_persona_repo: FakeBuyerPersonaRepository,
    product_repo: FakeProductRepository,
) -> ContactService:
    return ContactService(
        contact_repository=contact_repo,
        company_repository=company_repo,
        buyer_persona_repository=buyer_persona_repo,
        product_repository=product_repo,
    )


def _create_payload(company_id: UUID, **overrides: object) -> ContactCreate:
    return ContactCreate(
        company_id=company_id,
        buyer_persona_id=overrides.get("buyer_persona_id"),  # type: ignore[arg-type]
        first_name=overrides.get("first_name", "Jane"),  # type: ignore[arg-type]
        last_name=overrides.get("last_name", "Doe"),  # type: ignore[arg-type]
        full_name=overrides.get("full_name"),  # type: ignore[arg-type]
        email=overrides.get("email"),  # type: ignore[arg-type]
        linkedin_url=overrides.get("linkedin_url"),  # type: ignore[arg-type]
        department=overrides.get("department"),  # type: ignore[arg-type]
        seniority=overrides.get("seniority"),  # type: ignore[arg-type]
        relationship_status=overrides.get("relationship_status", RelationshipStatus.COLD),  # type: ignore[arg-type]
        influence_score=overrides.get("influence_score"),  # type: ignore[arg-type]
        engagement_score=overrides.get("engagement_score"),  # type: ignore[arg-type]
        confidence_score=overrides.get("confidence_score"),  # type: ignore[arg-type]
    )


# ── CRUD tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_contact(
    service: ContactService, contact_repo: FakeContactRepository, company_id: UUID
) -> None:
    contact = await service.create(_create_payload(company_id, first_name="Alice", last_name="Smith"))

    assert contact.id is not None
    assert contact.full_name == "Alice Smith"
    assert contact.company_id == company_id
    assert contact.status == ContactStatus.NEW
    assert contact_repo.commits == 1


@pytest.mark.asyncio
async def test_create_contact_company_not_found(service: ContactService) -> None:
    with pytest.raises(ContactCompanyNotFoundError):
        await service.create(_create_payload(uuid4()))


@pytest.mark.asyncio
async def test_full_name_explicit_override_respected(service: ContactService, company_id: UUID) -> None:
    contact = await service.create(
        _create_payload(company_id, first_name="Wei", last_name="Zhang", full_name="Zhang Wei")
    )
    assert contact.full_name == "Zhang Wei"


@pytest.mark.asyncio
async def test_get_contact(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id))
    fetched = await service.get(created.id)
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_contact_not_found(service: ContactService) -> None:
    with pytest.raises(ContactNotFoundError):
        await service.get(uuid4())


@pytest.mark.asyncio
async def test_update_contact(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id))
    updated = await service.update(created.id, ContactUpdate(job_title="VP Sales"))
    assert updated.job_title == "VP Sales"


@pytest.mark.asyncio
async def test_update_recomputes_full_name(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id, first_name="Jane", last_name="Doe"))
    updated = await service.update(created.id, ContactUpdate(last_name="Smith"))
    assert updated.full_name == "Jane Smith"


@pytest.mark.asyncio
async def test_cannot_update_archived_contact(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id))
    await service.archive(created.id)

    with pytest.raises(ContactBusinessRuleError, match="archived"):
        await service.update(created.id, ContactUpdate(job_title="New Title"))


# ── Email normalization & duplicate detection ─────────────────────────────────

@pytest.mark.asyncio
async def test_email_normalized_to_lowercase(service: ContactService, company_id: UUID) -> None:
    contact = await service.create(_create_payload(company_id, email=" John.Doe@ACME.com "))
    assert contact.email == "john.doe@acme.com"


@pytest.mark.asyncio
async def test_duplicate_email_within_company_rejected(service: ContactService, company_id: UUID) -> None:
    await service.create(_create_payload(company_id, first_name="A", email="dup@acme.com"))

    with pytest.raises(ContactDuplicateEmailError):
        await service.create(_create_payload(company_id, first_name="B", email="dup@acme.com"))


@pytest.mark.asyncio
async def test_duplicate_email_case_insensitive(service: ContactService, company_id: UUID) -> None:
    await service.create(_create_payload(company_id, first_name="A", email="dup@acme.com"))

    with pytest.raises(ContactDuplicateEmailError):
        await service.create(_create_payload(company_id, first_name="B", email="DUP@ACME.COM"))


@pytest.mark.asyncio
async def test_same_email_allowed_across_companies(
    service: ContactService, company_id: UUID, other_company_id: UUID
) -> None:
    a = await service.create(_create_payload(company_id, email="shared@acme.com"))
    b = await service.create(_create_payload(other_company_id, email="shared@acme.com"))
    assert a.id != b.id


@pytest.mark.asyncio
async def test_multiple_contacts_without_email_allowed(service: ContactService, company_id: UUID) -> None:
    a = await service.create(_create_payload(company_id, first_name="A"))
    b = await service.create(_create_payload(company_id, first_name="B"))
    assert a.id != b.id


@pytest.mark.asyncio
async def test_update_to_duplicate_email_rejected(service: ContactService, company_id: UUID) -> None:
    await service.create(_create_payload(company_id, first_name="A", email="taken@acme.com"))
    other = await service.create(_create_payload(company_id, first_name="B", email="other@acme.com"))

    with pytest.raises(ContactDuplicateEmailError):
        await service.update(other.id, ContactUpdate(email="taken@acme.com"))


# ── LinkedIn normalization & duplicate detection ──────────────────────────────

@pytest.mark.asyncio
async def test_linkedin_url_normalized(service: ContactService, company_id: UUID) -> None:
    contact = await service.create(
        _create_payload(company_id, linkedin_url="HTTPS://WWW.LinkedIn.com/in/JaneDoe/?utm=x")
    )
    assert contact.linkedin_url == "https://linkedin.com/in/JaneDoe"


@pytest.mark.asyncio
async def test_duplicate_linkedin_within_company_rejected(service: ContactService, company_id: UUID) -> None:
    await service.create(
        _create_payload(company_id, first_name="A", linkedin_url="https://linkedin.com/in/janedoe")
    )
    with pytest.raises(ContactDuplicateLinkedInError):
        await service.create(
            _create_payload(company_id, first_name="B", linkedin_url="https://www.linkedin.com/in/janedoe/")
        )


# ── Buyer persona validation (two-hop) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_buyer_persona_must_belong_to_same_workspace(
    service: ContactService,
    buyer_persona_repo: FakeBuyerPersonaRepository,
    product_repo: FakeProductRepository,
    company_id: UUID,
    other_workspace_id: UUID,
) -> None:
    foreign_product_id = uuid4()
    product_repo.register(foreign_product_id, other_workspace_id)
    foreign_persona_id = uuid4()
    buyer_persona_repo.register(foreign_persona_id, foreign_product_id)

    with pytest.raises(ContactBuyerPersonaNotFoundError):
        await service.create(_create_payload(company_id, buyer_persona_id=foreign_persona_id))


@pytest.mark.asyncio
async def test_buyer_persona_in_same_workspace_accepted(
    service: ContactService,
    buyer_persona_repo: FakeBuyerPersonaRepository,
    product_repo: FakeProductRepository,
    company_id: UUID,
    workspace_id: UUID,
) -> None:
    product_id = uuid4()
    product_repo.register(product_id, workspace_id)
    persona_id = uuid4()
    buyer_persona_repo.register(persona_id, product_id)

    contact = await service.create(_create_payload(company_id, buyer_persona_id=persona_id))
    assert contact.buyer_persona_id == persona_id


@pytest.mark.asyncio
async def test_nonexistent_buyer_persona_rejected(service: ContactService, company_id: UUID) -> None:
    with pytest.raises(ContactBuyerPersonaNotFoundError):
        await service.create(_create_payload(company_id, buyer_persona_id=uuid4()))


@pytest.mark.asyncio
async def test_buyer_persona_optional(service: ContactService, company_id: UUID) -> None:
    contact = await service.create(_create_payload(company_id))
    assert contact.buyer_persona_id is None


# ── Score validation ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_valid_scores_accepted(service: ContactService, company_id: UUID) -> None:
    contact = await service.create(
        _create_payload(company_id, influence_score=70, engagement_score=50, confidence_score=90)
    )
    assert contact.influence_score == 70


def test_score_out_of_range_rejected_by_schema(company_id: UUID = uuid4()) -> None:
    with pytest.raises(ValueError):
        ContactCreate(company_id=company_id, first_name="A", last_name="B", influence_score=101)


def test_negative_score_rejected_by_schema(company_id: UUID = uuid4()) -> None:
    with pytest.raises(ValueError):
        ContactCreate(company_id=company_id, first_name="A", last_name="B", engagement_score=-5)


@pytest.mark.asyncio
async def test_update_scores_convenience_method(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id))
    updated = await service.update_scores(created.id, influence_score=88)
    assert updated.influence_score == 88


# ── Archive / Restore / Verify ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_archive_contact(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id))
    archived = await service.archive(created.id)
    assert archived.status == ContactStatus.ARCHIVED


@pytest.mark.asyncio
async def test_cannot_archive_already_archived_contact(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id))
    await service.archive(created.id)

    with pytest.raises(ContactInvalidTransitionError):
        await service.archive(created.id)


@pytest.mark.asyncio
async def test_restore_archived_contact(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id))
    await service.archive(created.id)

    restored = await service.restore(created.id)
    assert restored.status == ContactStatus.NEW


@pytest.mark.asyncio
async def test_cannot_restore_non_archived_contact(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id))

    with pytest.raises(ContactInvalidTransitionError):
        await service.restore(created.id)


@pytest.mark.asyncio
async def test_verify_contact(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id))
    verified = await service.verify(created.id)
    assert verified.status == ContactStatus.VERIFIED


@pytest.mark.asyncio
async def test_cannot_verify_archived_contact(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id))
    await service.archive(created.id)

    with pytest.raises(ContactInvalidTransitionError):
        await service.verify(created.id)


# ── Relationship status change event ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_relationship_status_update(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id, relationship_status=RelationshipStatus.COLD))
    updated = await service.update(created.id, ContactUpdate(relationship_status=RelationshipStatus.WARM))
    assert updated.relationship_status == RelationshipStatus.WARM


# ── Soft delete ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id))
    assert created.deleted_at is None

    await service.delete(created.id)
    assert created.deleted_at is not None


@pytest.mark.asyncio
async def test_soft_deleted_contact_excluded_from_list(service: ContactService, company_id: UUID) -> None:
    keep = await service.create(_create_payload(company_id, first_name="Keep"))
    delete_me = await service.create(
        _create_payload(company_id, first_name="Delete", email="delete@acme.com")
    )
    await service.delete(delete_me.id)

    contacts, total = await service.list(company_id=company_id)
    assert total == 1
    assert contacts[0].id == keep.id


@pytest.mark.asyncio
async def test_soft_deleted_contact_not_found_by_id(service: ContactService, company_id: UUID) -> None:
    created = await service.create(_create_payload(company_id))
    await service.delete(created.id)

    with pytest.raises(ContactNotFoundError):
        await service.get(created.id)


# ── Workspace isolation (via company scoping) ─────────────────────────────────

@pytest.mark.asyncio
async def test_contact_company_isolation(
    service: ContactService, company_id: UUID, other_company_id: UUID
) -> None:
    await service.create(_create_payload(company_id, first_name="CompanyA"))
    await service.create(_create_payload(other_company_id, first_name="CompanyB"))

    contacts_a, total_a = await service.list(company_id=company_id)
    contacts_b, total_b = await service.list(company_id=other_company_id)

    assert total_a == 1
    assert total_b == 1
    assert contacts_a[0].first_name == "CompanyA"
    assert contacts_b[0].first_name == "CompanyB"
    # company_id and other_company_id belong to different workspaces (see fixtures),
    # so this also proves cross-workspace isolation transitively.


# ── Search & filters ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_by_name(service: ContactService, company_id: UUID) -> None:
    await service.create(_create_payload(company_id, first_name="Alice", last_name="Anderson"))
    await service.create(_create_payload(company_id, first_name="Bob", last_name="Brown"))

    results, total = await service.list(company_id=company_id, search="Alice")
    assert total == 1
    assert results[0].first_name == "Alice"


@pytest.mark.asyncio
async def test_filter_by_department(service: ContactService, company_id: UUID) -> None:
    await service.create(_create_payload(company_id, first_name="Eng", department="Engineering"))
    await service.create(_create_payload(company_id, first_name="Sales", department="Sales"))

    results, total = await service.list(company_id=company_id, department="Engineering")
    assert total == 1
    assert results[0].first_name == "Eng"


@pytest.mark.asyncio
async def test_filter_by_seniority(service: ContactService, company_id: UUID) -> None:
    await service.create(_create_payload(company_id, first_name="VP", seniority=SeniorityLevel.VP))
    await service.create(_create_payload(company_id, first_name="Mgr", seniority=SeniorityLevel.MANAGER))

    results, total = await service.list(company_id=company_id, seniority=SeniorityLevel.VP)
    assert total == 1
    assert results[0].first_name == "VP"


# ── Pagination ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_pagination(service: ContactService, company_id: UUID) -> None:
    for i in range(5):
        await service.create(_create_payload(company_id, first_name=f"Contact{i}"))

    page1, total = await service.list(company_id=company_id, offset=0, limit=2)
    page2, _ = await service.list(company_id=company_id, offset=2, limit=2)
    page3, _ = await service.list(company_id=company_id, offset=4, limit=2)

    assert total == 5
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1
