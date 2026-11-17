import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.document import Document


class DocumentChunk(Base, TimestampMixin):
    """DocumentChunk entity holding text passages and pgvector embeddings."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    text_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    # 1536 is standard for OpenAI text-embedding-3-small and compatible models
    embedding = mapped_column(
        Vector(settings.EMBEDDING_DIMENSIONS),
        nullable=True,
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
    )
