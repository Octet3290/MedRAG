import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from app.security.deps import get_current_user
from app.services.knowledge_base import knowledge_base_service

router = APIRouter(prefix="/knowledge-bases", tags=["Knowledge Bases"])


@router.post(
    "",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new knowledge base",
)
async def create_knowledge_base(
    obj_in: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseResponse:
    """Create a new knowledge base owned by the authenticated user."""
    kb = await knowledge_base_service.create_knowledge_base(
        db,
        obj_in=obj_in,
        current_user=current_user,
    )
    return KnowledgeBaseResponse.model_validate(kb)


@router.get(
    "",
    response_model=KnowledgeBaseListResponse,
    summary="List user's knowledge bases",
)
async def list_knowledge_bases(
    skip: int = Query(default=0, ge=0, description="Offset for pagination"),
    limit: int = Query(default=50, ge=1, le=100, description="Page limit"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseListResponse:
    """Retrieve all knowledge bases owned by the authenticated user."""
    items, total = await knowledge_base_service.list_knowledge_bases(
        db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )
    return KnowledgeBaseListResponse(
        items=[KnowledgeBaseResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get(
    "/{kb_id}",
    response_model=KnowledgeBaseResponse,
    summary="Get a knowledge base by ID",
)
async def get_knowledge_base(
    kb_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseResponse:
    """Retrieve details of a single knowledge base by ID."""
    kb = await knowledge_base_service.get_knowledge_base(
        db,
        kb_id=kb_id,
        current_user=current_user,
    )
    return KnowledgeBaseResponse.model_validate(kb)


@router.patch(
    "/{kb_id}",
    response_model=KnowledgeBaseResponse,
    summary="Update a knowledge base",
)
async def update_knowledge_base(
    kb_id: uuid.UUID,
    obj_in: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseResponse:
    """Update name or description of an existing knowledge base."""
    kb = await knowledge_base_service.update_knowledge_base(
        db,
        kb_id=kb_id,
        obj_in=obj_in,
        current_user=current_user,
    )
    return KnowledgeBaseResponse.model_validate(kb)


@router.delete(
    "/{kb_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a knowledge base",
)
async def delete_knowledge_base(
    kb_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a knowledge base and all associated documents, chunks, and conversations."""
    await knowledge_base_service.delete_knowledge_base(
        db,
        kb_id=kb_id,
        current_user=current_user,
    )
