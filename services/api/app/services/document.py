import hashlib
import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document
from app.models.user import User
from app.rag.chunker import chunk_pages
from app.rag.embeddings import embedding_service
from app.rag.extractor import extract_text_from_file, validate_file_magic_bytes
from app.repositories.chunk import chunk_repo
from app.repositories.document import document_repo
from app.services.knowledge_base import knowledge_base_service


class DocumentService:
    """Service handling document validation, storage, chunking, embeddings, and authorization."""

    def _ensure_upload_dir(self) -> str:
        upload_path = os.path.abspath(settings.UPLOAD_DIR)
        os.makedirs(upload_path, exist_ok=True)
        return upload_path

    async def _process_and_index_document(
        self,
        db: AsyncSession,
        *,
        doc: Document,
        content: bytes,
        filename: str,
    ) -> Document:
        """Extract text, generate chunks, compute embeddings, and store in pgvector."""
        try:
            # 1. Text extraction
            pages = extract_text_from_file(content, filename)

            # 2. Structure-aware chunking with token overlap
            chunks = chunk_pages(
                pages,
                chunk_size=settings.CHUNK_SIZE_TOKENS,
                chunk_overlap=settings.CHUNK_OVERLAP_TOKENS,
            )

            # 3. Batched embedding generation
            chunk_texts = [c.text for c in chunks]
            embeddings = await embedding_service.embed_batch(chunk_texts)

            # 4. Prepare records for bulk insert
            chunks_data = [
                {
                    "chunk_index": chunk.chunk_index,
                    "text_content": chunk.text,
                    "page_number": chunk.page_number,
                    "chunk_metadata": {
                        "token_count": chunk.token_count,
                        "original_filename": filename,
                    },
                    "embedding": emb,
                }
                for chunk, emb in zip(chunks, embeddings, strict=True)
            ]

            # Clear any stale chunks before writing new ones (idempotency)
            await chunk_repo.delete_by_document(db, document_id=doc.id)
            await chunk_repo.bulk_create(db, document_id=doc.id, chunks_data=chunks_data)

            # Update document to ready
            return await document_repo.update_status(
                db,
                db_obj=doc,
                status="ready",
                error_summary=None,
            )

        except Exception as e:
            return await document_repo.update_status(
                db,
                db_obj=doc,
                status="failed",
                error_summary=str(e),
            )

    async def upload_document(
        self,
        db: AsyncSession,
        *,
        kb_id: uuid.UUID,
        upload_file: UploadFile,
        current_user: User,
        background: bool = False,
    ) -> Document:
        # 1. Enforce Knowledge Base ownership
        await knowledge_base_service.get_knowledge_base(db, kb_id=kb_id, current_user=current_user)

        # 2. Read and enforce size limits
        filename = upload_file.filename or "unnamed_document"
        content = await upload_file.read()
        file_size = len(content)

        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {max_mb} MB.",
            )

        # 3. Validate magic bytes and format
        try:
            detected_mime = validate_file_magic_bytes(content, filename)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

        # 4. Save to disk using safe UUID key
        checksum = hashlib.sha256(content).hexdigest()
        storage_id = uuid.uuid4().hex
        safe_extension = ".pdf" if detected_mime == "application/pdf" else ".txt"
        storage_key = f"{storage_id}{safe_extension}"

        upload_dir = self._ensure_upload_dir()
        physical_path = os.path.join(upload_dir, storage_key)

        with open(physical_path, "wb") as f:
            f.write(content)

        # 5. Persist document record initially as "processing"
        doc = await document_repo.create(
            db,
            knowledge_base_id=kb_id,
            uploaded_by=current_user.id,
            original_filename=filename,
            storage_key=storage_key,
            mime_type=detected_mime,
            file_size_bytes=file_size,
            checksum=checksum,
            status="processing",
        )

        # 6. If background is True, caller handles async worker task
        if background:
            return doc

        # Otherwise extract, chunk, embed, and store synchronously
        return await self._process_and_index_document(
            db,
            doc=doc,
            content=content,
            filename=filename,
        )

    async def get_document(
        self,
        db: AsyncSession,
        *,
        doc_id: uuid.UUID,
        current_user: User,
    ) -> Document:
        doc = await document_repo.get_by_id(db, doc_id=doc_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )
        await knowledge_base_service.get_knowledge_base(
            db, kb_id=doc.knowledge_base_id, current_user=current_user
        )
        return doc

    async def list_documents(
        self,
        db: AsyncSession,
        *,
        kb_id: uuid.UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Document], int]:
        await knowledge_base_service.get_knowledge_base(db, kb_id=kb_id, current_user=current_user)
        return await document_repo.list_by_knowledge_base(db, kb_id=kb_id, skip=skip, limit=limit)

    async def delete_document(
        self,
        db: AsyncSession,
        *,
        doc_id: uuid.UUID,
        current_user: User,
    ) -> None:
        doc = await self.get_document(db, doc_id=doc_id, current_user=current_user)

        # Delete physical file from disk
        upload_dir = self._ensure_upload_dir()
        file_path = os.path.join(upload_dir, doc.storage_key)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        # Delete database record (cascades to chunks)
        await document_repo.delete(db, db_obj=doc)

    async def reindex_document(
        self,
        db: AsyncSession,
        *,
        doc_id: uuid.UUID,
        current_user: User,
        background: bool = False,
    ) -> Document:
        """Idempotently re-extract, re-chunk, and re-embed an uploaded document from disk."""
        doc = await self.get_document(db, doc_id=doc_id, current_user=current_user)

        upload_dir = self._ensure_upload_dir()
        file_path = os.path.join(upload_dir, doc.storage_key)
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical document file missing from server storage.",
            )

        if background:
            return await document_repo.update_status(
                db,
                db_obj=doc,
                status="processing",
                error_summary=None,
            )

        with open(file_path, "rb") as f:
            content = f.read()

        return await self._process_and_index_document(
            db,
            doc=doc,
            content=content,
            filename=doc.original_filename,
        )


document_service = DocumentService()
