import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate


class KnowledgeBaseRepository:
    """Repository handling SQL persistence for KnowledgeBase entities."""

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: KnowledgeBaseCreate,
        owner_id: uuid.UUID,
    ) -> KnowledgeBase:
        db_obj = KnowledgeBase(
            name=obj_in.name.strip(),
            description=obj_in.description.strip() if obj_in.description else None,
            owner_id=owner_id,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        kb_id: uuid.UUID,
    ) -> KnowledgeBase | None:
        query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_owner(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[KnowledgeBase], int]:
        # Count total records for pagination
        count_query = select(func.count(KnowledgeBase.id)).where(KnowledgeBase.owner_id == owner_id)
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Query items with pagination and ordering
        items_query = (
            select(KnowledgeBase)
            .where(KnowledgeBase.owner_id == owner_id)
            .order_by(KnowledgeBase.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items_result = await db.execute(items_query)
        items = list(items_result.scalars().all())

        return items, total

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: KnowledgeBase,
        obj_in: KnowledgeBaseUpdate,
    ) -> KnowledgeBase:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None and isinstance(value, str):
                setattr(db_obj, field, value.strip())
            else:
                setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self,
        db: AsyncSession,
        *,
        db_obj: KnowledgeBase,
    ) -> None:
        await db.delete(db_obj)
        await db.commit()


knowledge_base_repo = KnowledgeBaseRepository()
