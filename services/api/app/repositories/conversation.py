import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message


class ConversationRepository:
    """Repository handling SQL operations for Conversations and Messages."""

    async def create_conversation(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        title: str,
    ) -> Conversation:
        """Create a new conversation session."""
        conv = Conversation(
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            title=title,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return conv

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        conversation_id: uuid.UUID,
    ) -> Conversation | None:
        """Fetch conversation by ID with messages eagerly loaded."""
        query = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        result = await db.execute(query)
        return result.scalars().first()

    async def list_by_knowledge_base(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[Conversation, int]], int]:
        """
        List conversations for a specific knowledge base and owner.
        Returns tuples of (Conversation, message_count) and total count.
        """
        # Count total
        count_query = select(func.count(Conversation.id)).where(
            Conversation.owner_id == owner_id,
            Conversation.knowledge_base_id == knowledge_base_id,
        )
        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        # Fetch conversations with message count via left join
        query = (
            select(Conversation, func.count(Message.id).label("message_count"))
            .outerjoin(Message, Conversation.id == Message.conversation_id)
            .where(
                Conversation.owner_id == owner_id,
                Conversation.knowledge_base_id == knowledge_base_id,
            )
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        rows = result.all()
        return [(row[0], row[1]) for row in rows], total

    async def update_title(
        self,
        db: AsyncSession,
        *,
        conversation: Conversation,
        title: str,
    ) -> Conversation:
        """Update conversation title."""
        conversation.title = title
        await db.commit()
        await db.refresh(conversation)
        return conversation

    async def delete(
        self,
        db: AsyncSession,
        *,
        conversation: Conversation,
    ) -> None:
        """Delete conversation and cascade delete its messages."""
        await db.delete(conversation)
        await db.commit()

    async def add_message(
        self,
        db: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        citations: list[dict[str, Any]] | None = None,
        model_metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Insert a new message into the conversation thread."""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations or [],
            model_metadata=model_metadata or {},
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    async def get_recent_messages(
        self,
        db: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        limit: int = 10,
    ) -> list[Message]:
        """Fetch the most recent messages for chat context in chronological order."""
        subquery = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .subquery()
        )
        query = select(Message).from_statement(
            select(subquery).order_by(subquery.c.created_at.asc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())


conversation_repo = ConversationRepository()
