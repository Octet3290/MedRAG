import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.repositories.chunk import chunk_repo
from app.schemas.chunk import ChunkListResponse, ChunkResponse
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.security.deps import get_current_user
from app.services.document import document_service
from app.workers.ingestion import process_document_task

router = APIRouter(tags=["Documents"])


@router.post(
    "/knowledge-bases/{kb_id}/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a document",
)
async def upload_document(
    kb_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF or TXT file to upload"),
    background: bool = Query(
        default=False,
        description="If True, processes document asynchronously in a background worker task.",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """
    Upload a document (PDF or TXT), validate format, and either process
    synchronously or dispatch to a background worker task.
    """
    doc = await document_service.upload_document(
        db,
        kb_id=kb_id,
        upload_file=file,
        current_user=current_user,
        background=background,
    )
    if background:
        background_tasks.add_task(process_document_task, doc.id)
    return DocumentResponse.model_validate(doc)


@router.get(
    "/knowledge-bases/{kb_id}/documents",
    response_model=DocumentListResponse,
    summary="List documents in a knowledge base",
)
async def list_documents(
    kb_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    """List all documents and processing statuses within a knowledge base."""
    items, total = await document_service.list_documents(
        db,
        kb_id=kb_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
async def get_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Retrieve details and processing status of a single document."""
    doc = await document_service.get_document(
        db,
        doc_id=doc_id,
        current_user=current_user,
    )
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a document, its physical storage file, and its associated chunks."""
    await document_service.delete_document(
        db,
        doc_id=doc_id,
        current_user=current_user,
    )


@router.post(
    "/documents/{doc_id}/reindex",
    response_model=DocumentResponse,
    summary="Reindex an existing document",
)
async def reindex_document(
    doc_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    background: bool = Query(
        default=False,
        description="If True, reindexes document asynchronously in a background worker task.",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """
    Idempotently re-extract, re-chunk, and re-embed a document.
    Clears old chunks and generates new embeddings.
    """
    doc = await document_service.reindex_document(
        db,
        doc_id=doc_id,
        current_user=current_user,
        background=background,
    )
    if background:
        background_tasks.add_task(process_document_task, doc.id)
    return DocumentResponse.model_validate(doc)


@router.get(
    "/documents/{doc_id}/chunks",
    response_model=ChunkListResponse,
    summary="Inspect chunks of a document",
)
async def get_document_chunks(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChunkListResponse:
    """Inspect indexed text chunks and page metadata for a document."""
    doc = await document_service.get_document(db, doc_id=doc_id, current_user=current_user)
    chunks = await chunk_repo.list_by_document(db, document_id=doc.id)
    return ChunkListResponse(
        items=[ChunkResponse.model_validate(c) for c in chunks],
        total=len(chunks),
    )
