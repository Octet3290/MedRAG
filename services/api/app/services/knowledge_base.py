import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.repositories.knowledge_base import knowledge_base_repo
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate


class KnowledgeBaseService:
    """Service layer coordinating business logic and authorization for Knowledge Bases."""

    async def create_knowledge_base(
        self,
        db: AsyncSession,
        *,
        obj_in: KnowledgeBaseCreate,
        current_user: User,
    ) -> KnowledgeBase:
        return await knowledge_base_repo.create(
            db,
            obj_in=obj_in,
            owner_id=current_user.id,
        )

    async def get_knowledge_base(
        self,
        db: AsyncSession,
        *,
        kb_id: uuid.UUID,
        current_user: User,
    ) -> KnowledgeBase:
        kb = await knowledge_base_repo.get_by_id(db, kb_id=kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )
        # Strict resource-level authorization
        if kb.owner_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this knowledge base",
            )
        return kb

    async def list_knowledge_bases(
        self,
        db: AsyncSession,
        *,
        current_user: User,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[KnowledgeBase], int]:
        return await knowledge_base_repo.list_by_owner(
            db,
            owner_id=current_user.id,
            skip=skip,
            limit=limit,
        )

    async def update_knowledge_base(
        self,
        db: AsyncSession,
        *,
        kb_id: uuid.UUID,
        obj_in: KnowledgeBaseUpdate,
        current_user: User,
    ) -> KnowledgeBase:
        kb = await self.get_knowledge_base(db, kb_id=kb_id, current_user=current_user)
        return await knowledge_base_repo.update(db, db_obj=kb, obj_in=obj_in)

    async def delete_knowledge_base(
        self,
        db: AsyncSession,
        *,
        kb_id: uuid.UUID,
        current_user: User,
    ) -> None:
        kb = await self.get_knowledge_base(db, kb_id=kb_id, current_user=current_user)
        await knowledge_base_repo.delete(db, db_obj=kb)


knowledge_base_service = KnowledgeBaseService()
