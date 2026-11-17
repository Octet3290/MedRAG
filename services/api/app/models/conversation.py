import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.knowledge_base import KnowledgeBase
    from app.models.user import User


class Conversation(Base, TimestampMixin):
    """Conversation entity tracking chat sessions scoped to a knowledge base."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        default="New Conversation",
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="conversations",
    )
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase",
        back_populates="conversations",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base, TimestampMixin):
    """Message entity storing question, answer, and grounded citations."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(50),  # "user", "assistant", "system"
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        default=list,
        nullable=True,
    )
    model_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        default=dict,
        nullable=True,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )
