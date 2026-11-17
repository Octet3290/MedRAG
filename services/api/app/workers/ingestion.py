import logging
import os
import uuid

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.rag.chunker import chunk_pages
from app.rag.embeddings import embedding_service
from app.rag.extractor import extract_text_from_file
from app.repositories.chunk import chunk_repo
from app.repositories.document import document_repo

logger = logging.getLogger("medrag.workers.ingestion")


async def process_document_task(document_id: uuid.UUID) -> None:
    """
    Durable Background Ingestion Worker Task:
    1. Fetches document by ID using an isolated database session.
    2. Marks document status as 'processing'.
    3. Reads physical content from storage.
    4. Extracts text per page.
    5. Chunks text with token overlap preservation.
    6. Generates vector embeddings in batched mode.
    7. Atomically clears old chunks and bulk-inserts new chunks and vectors.
    8. Updates document status to 'ready' (or 'failed' on error with error_summary).
    """
    logger.info("Starting background ingestion task for document %s", document_id)

    async with AsyncSessionLocal() as session:
        doc = await document_repo.get_by_id(session, doc_id=document_id)
        if not doc:
            logger.error(
                "Document %s not found in database during background ingestion",
                document_id,
            )
            return

        try:
            # 1. Update status to 'processing'
            doc = await document_repo.update_status(
                session,
                db_obj=doc,
                status="processing",
                error_summary=None,
            )

            # 2. Locate and read physical file from server storage
            upload_path = os.path.abspath(settings.UPLOAD_DIR)
            file_path = os.path.join(upload_path, doc.storage_key)

            if not os.path.exists(file_path):
                raise FileNotFoundError(
                    f"Physical storage file '{doc.storage_key}' not found on server disk."
                )

            with open(file_path, "rb") as f:
                content = f.read()

            # 3. Extract text per-page
            pages = extract_text_from_file(content, doc.original_filename)

            # 4. Structure-aware chunking with token overlap
            chunks = chunk_pages(
                pages,
                chunk_size=settings.CHUNK_SIZE_TOKENS,
                chunk_overlap=settings.CHUNK_OVERLAP_TOKENS,
            )

            # 5. Batched embedding generation
            chunk_texts = [c.text for c in chunks]
            embeddings = await embedding_service.embed_batch(chunk_texts)

            # 6. Format chunks for bulk insert
            chunks_data = [
                {
                    "chunk_index": chunk.chunk_index,
                    "text_content": chunk.text,
                    "page_number": chunk.page_number,
                    "chunk_metadata": {
                        "token_count": chunk.token_count,
                        "original_filename": doc.original_filename,
                    },
                    "embedding": emb,
                }
                for chunk, emb in zip(chunks, embeddings, strict=True)
            ]

            # 7. Atomic transaction: purge stale chunks, insert new chunks
            await chunk_repo.delete_by_document(session, document_id=doc.id)
            await chunk_repo.bulk_create(session, document_id=doc.id, chunks_data=chunks_data)

            # 8. Mark document as ready
            await document_repo.update_status(
                session,
                db_obj=doc,
                status="ready",
                error_summary=None,
            )
            logger.info(
                "Document %s successfully processed and indexed (%d chunks)",
                document_id,
                len(chunks_data),
            )

        except Exception as exc:
            logger.exception("Background ingestion failed for document %s: %s", document_id, exc)
            try:
                await document_repo.update_status(
                    session,
                    db_obj=doc,
                    status="failed",
                    error_summary=str(exc)[:500],
                )
            except Exception as update_err:
                logger.error(
                    "Failed to record failure status for document %s: %s",
                    document_id,
                    update_err,
                )
