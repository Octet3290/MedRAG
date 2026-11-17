import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.conversation import (
    ChatTurnResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    ConversationUpdate,
    SendMessageRequest,
)
from app.security.deps import get_current_user
from app.services.chat import chat_service

router = APIRouter(tags=["Conversations & Multi-Turn Chat"])


@router.post(
    "/knowledge-bases/{kb_id}/conversations",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation session inside a knowledge base",
)
async def create_conversation(
    kb_id: uuid.UUID,
    obj_in: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationDetailResponse:
    conv = await chat_service.create_conversation(
        db,
        kb_id=kb_id,
        obj_in=obj_in,
        current_user=current_user,
    )
    return await chat_service.get_conversation(
        db,
        conversation_id=conv.id,
        current_user=current_user,
    )


@router.get(
    "/knowledge-bases/{kb_id}/conversations",
    response_model=ConversationListResponse,
    summary="List all conversations in a knowledge base for the current user",
)
async def list_conversations(
    kb_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationListResponse:
    return await chat_service.list_conversations(
        db,
        kb_id=kb_id,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Fetch full conversation detail with ordered message thread",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationDetailResponse:
    return await chat_service.get_conversation(
        db,
        conversation_id=conversation_id,
        current_user=current_user,
    )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationSummary,
    summary="Rename conversation title",
)
async def update_conversation_title(
    conversation_id: uuid.UUID,
    obj_in: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationSummary:
    return await chat_service.update_title(
        db,
        conversation_id=conversation_id,
        obj_in=obj_in,
        current_user=current_user,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete conversation session and all its messages",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await chat_service.delete_conversation(
        db,
        conversation_id=conversation_id,
        current_user=current_user,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatTurnResponse,
    status_code=status.HTTP_200_OK,
    summary="Post a user message, perform contextual reformulation, and generate a grounded reply",
)
async def send_chat_message(
    conversation_id: uuid.UUID,
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatTurnResponse:
    return await chat_service.post_message_and_respond(
        db,
        conversation_id=conversation_id,
        request=request,
        current_user=current_user,
    )
