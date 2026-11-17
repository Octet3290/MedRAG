import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chunk import DocumentChunk
from app.models.document import Document


class DocumentChunkRepository:
    """Repository handling SQL and pgvector similarity queries for DocumentChunk entities."""

    async def bulk_create(
        self,
        db: AsyncSession,
        *,
        document_id: uuid.UUID,
        chunks_data: list[dict[str, Any]],
    ) -> list[DocumentChunk]:
        """Insert multiple document chunks and their embeddings in a single transaction."""
        chunk_objects: list[DocumentChunk] = []
        for data in chunks_data:
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=data["chunk_index"],
                text_content=data["text_content"],
                page_number=data.get("page_number"),
                chunk_metadata=data.get("chunk_metadata", {}),
                embedding=data["embedding"],
            )
            chunk_objects.append(chunk)

        db.add_all(chunk_objects)
        await db.commit()
        return chunk_objects

    async def delete_by_document(
        self,
        db: AsyncSession,
        *,
        document_id: uuid.UUID,
    ) -> None:
        """Delete all existing chunks for a document (idempotent re-indexing)."""
        stmt = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        await db.execute(stmt)
        await db.commit()

    async def list_by_document(
        self,
        db: AsyncSession,
        *,
        document_id: uuid.UUID,
    ) -> list[DocumentChunk]:
        """Fetch all chunks belonging to a document ordered by chunk_index."""
        query = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def search_similar_chunks(
        self,
        db: AsyncSession,
        *,
        knowledge_base_id: uuid.UUID,
        query_vector: list[float],
        top_k: int = 4,
        similarity_threshold: float | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Perform vector similarity search using pgvector cosine distance (<=>).
        Returns a list of (DocumentChunk, cosine_distance) tuples.
        Cosine distance = 1 - cosine_similarity.
        A smaller distance indicates higher semantic relevance.
        """
        distance_col = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")

        query = (
            select(DocumentChunk, distance_col)
            .join(Document, DocumentChunk.document_id == Document.id)
            .options(selectinload(DocumentChunk.document))
            .where(
                Document.knowledge_base_id == knowledge_base_id,
                Document.status == "ready",
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(distance_col.asc())
            .limit(top_k)
        )

        result = await db.execute(query)
        rows = result.all()

        results: list[tuple[DocumentChunk, float]] = []
        for chunk, dist in rows:
            float_dist = float(dist)
            if similarity_threshold is not None:
                # If similarity_threshold provided (e.g. 0.75), distance must be <= (1 - threshold)
                if float_dist > (1.0 - similarity_threshold):
                    continue
            results.append((chunk, float_dist))

        return results


chunk_repo = DocumentChunkRepository()
