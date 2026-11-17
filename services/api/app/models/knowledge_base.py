import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.document import Document
    from app.models.user import User


class KnowledgeBase(Base, TimestampMixin):
    """KnowledgeBase entity grouping documents and scoped vector searches."""

    __tablename__ = "knowledge_bases"

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
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="knowledge_bases",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
    )
