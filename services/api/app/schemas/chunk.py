import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ChunkResponse(BaseModel):
    """Schema representing an indexed document chunk (excluding raw float vector)."""

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    text_content: str
    page_number: int | None = None
    chunk_metadata: dict[str, Any] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChunkListResponse(BaseModel):
    """List of chunks for an indexed document."""

    items: list[ChunkResponse]
    total: int
