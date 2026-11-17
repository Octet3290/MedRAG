import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """Sanitized document metadata response."""

    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    uploaded_by: uuid.UUID | None = None
    original_filename: str
    mime_type: str
    file_size_bytes: int
    status: str
    error_summary: str | None = None
    ingestion_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Paginated list of documents inside a knowledge base."""

    items: list[DocumentResponse]
    total: int
