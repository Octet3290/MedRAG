import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.chunk import DocumentChunk
    from app.models.knowledge_base import KnowledgeBase


class Document(Base, TimestampMixin):
    """Document entity tracking uploaded files and ingestion state."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    checksum: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="uploaded",
        nullable=False,
        index=True,
    )
    error_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    ingestion_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    # Relationships
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase",
        back_populates="documents",
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )
