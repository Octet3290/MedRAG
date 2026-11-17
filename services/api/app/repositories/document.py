import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    """Repository managing Document persistence in PostgreSQL."""

    async def create(
        self,
        db: AsyncSession,
        *,
        knowledge_base_id: uuid.UUID,
        uploaded_by: uuid.UUID | None,
        original_filename: str,
        storage_key: str,
        mime_type: str,
        file_size_bytes: int,
        checksum: str | None = None,
        status: str = "uploaded",
    ) -> Document:
        doc = Document(
            knowledge_base_id=knowledge_base_id,
            uploaded_by=uploaded_by,
            original_filename=original_filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            checksum=checksum,
            status=status,
            ingestion_version=1,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return doc

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        doc_id: uuid.UUID,
    ) -> Document | None:
        query = select(Document).where(Document.id == doc_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_knowledge_base(
        self,
        db: AsyncSession,
        *,
        kb_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Document], int]:
        count_query = select(func.count(Document.id)).where(Document.knowledge_base_id == kb_id)
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        items_query = (
            select(Document)
            .where(Document.knowledge_base_id == kb_id)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items_result = await db.execute(items_query)
        items = list(items_result.scalars().all())

        return items, total

    async def update_status(
        self,
        db: AsyncSession,
        *,
        db_obj: Document,
        status: str,
        error_summary: str | None = None,
    ) -> Document:
        db_obj.status = status
        db_obj.error_summary = error_summary
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self,
        db: AsyncSession,
        *,
        db_obj: Document,
    ) -> None:
        await db.delete(db_obj)
        await db.commit()


document_repo = DocumentRepository()
