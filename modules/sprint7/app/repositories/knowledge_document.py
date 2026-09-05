from uuid import UUID

from sqlalchemy import Select, cast, func, or_, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import String as SAString

from app.models.knowledge_document import DocumentType, KnowledgeDocument, KnowledgeStatus, SourceType


class KnowledgeRepository:
    """
    Pure data-access layer: CRUD, pagination, search (title/tags), product
    filtering, and version lookup only. No business rules live here — see
    KnowledgeService for duplicate detection, versioning, and archiving.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: KnowledgeDocument) -> KnowledgeDocument:
        self._session.add(document)
        await self._session.flush()
        await self._session.refresh(document)
        return document

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        tags: list[str] | None = None,
        document_type: DocumentType | None = None,
        source_type: SourceType | None = None,
        status: KnowledgeStatus | None = None,
    ) -> tuple[list[KnowledgeDocument], int]:
        statement = self._base_list_statement(
            product_id=product_id,
            search=search,
            tags=tags,
            document_type=document_type,
            source_type=source_type,
            status=status,
        )
        count_statement = select(func.count()).select_from(statement.subquery())

        documents_result = await self._session.execute(
            statement.order_by(KnowledgeDocument.created_at.desc()).offset(offset).limit(limit)
        )
        count_result = await self._session.execute(count_statement)

        return list(documents_result.scalars().all()), count_result.scalar_one()

    async def get_by_id(
        self, document_id: UUID, product_id: UUID | None = None
    ) -> KnowledgeDocument | None:
        filters = [KnowledgeDocument.id == document_id, KnowledgeDocument.deleted_at.is_(None)]
        if product_id is not None:
            filters.append(KnowledgeDocument.product_id == product_id)

        statement = select(KnowledgeDocument).where(*filters)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_checksum(self, checksum: str, product_id: UUID) -> KnowledgeDocument | None:
        """Used by KnowledgeService to detect duplicate content within a product."""
        statement = select(KnowledgeDocument).where(
            KnowledgeDocument.product_id == product_id,
            KnowledgeDocument.checksum == checksum,
            KnowledgeDocument.deleted_at.is_(None),
            KnowledgeDocument.status != KnowledgeStatus.ARCHIVED,
        )
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def get_active_by_title(self, title: str, product_id: UUID) -> KnowledgeDocument | None:
        """The current published version of a document family, if any."""
        statement = select(KnowledgeDocument).where(
            KnowledgeDocument.product_id == product_id,
            KnowledgeDocument.title == title,
            KnowledgeDocument.status == KnowledgeStatus.ACTIVE,
            KnowledgeDocument.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_version(self, title: str, product_id: UUID) -> KnowledgeDocument | None:
        """Highest version number for a document family, regardless of status."""
        statement = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.product_id == product_id,
                KnowledgeDocument.title == title,
                KnowledgeDocument.deleted_at.is_(None),
            )
            .order_by(KnowledgeDocument.version.desc())
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_versions(self, title: str, product_id: UUID) -> list[KnowledgeDocument]:
        """All non-deleted versions of a document family, newest first."""
        statement = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.product_id == product_id,
                KnowledgeDocument.title == title,
                KnowledgeDocument.deleted_at.is_(None),
            )
            .order_by(KnowledgeDocument.version.desc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_version(
        self, title: str, product_id: UUID, version: int
    ) -> KnowledgeDocument | None:
        statement = select(KnowledgeDocument).where(
            KnowledgeDocument.product_id == product_id,
            KnowledgeDocument.title == title,
            KnowledgeDocument.version == version,
            KnowledgeDocument.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def update(self, document: KnowledgeDocument) -> KnowledgeDocument:
        await self._session.flush()
        await self._session.refresh(document)
        return document

    async def soft_delete(self, document: KnowledgeDocument) -> KnowledgeDocument:
        await self._session.flush()
        await self._session.refresh(document)
        return document

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    def _base_list_statement(
        self,
        *,
        product_id: UUID,
        search: str | None,
        tags: list[str] | None,
        document_type: DocumentType | None,
        source_type: SourceType | None,
        status: KnowledgeStatus | None,
    ) -> Select[tuple[KnowledgeDocument]]:
        statement = select(KnowledgeDocument).where(
            KnowledgeDocument.product_id == product_id,
            KnowledgeDocument.deleted_at.is_(None),
        )

        if status is not None:
            statement = statement.where(KnowledgeDocument.status == status)

        if document_type is not None:
            statement = statement.where(KnowledgeDocument.document_type == document_type)

        if source_type is not None:
            statement = statement.where(KnowledgeDocument.source_type == source_type)

        if search:
            query = f"%{search.strip()}%"
            statement = statement.where(KnowledgeDocument.title.ilike(query))

        if tags:
            # Match documents whose `tags` JSONB array contains ANY of the given tags.
            statement = statement.where(
                KnowledgeDocument.tags.op("?|")(cast(tags, ARRAY(SAString)))
            )

        return statement
