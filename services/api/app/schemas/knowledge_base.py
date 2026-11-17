import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Descriptive name of the knowledge base",
        examples=["Cardiology Research 2026"],
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional detailed description of the knowledge base scope",
        examples=["Peer-reviewed clinical papers on arrhythmia treatment."],
    )


class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated name",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Updated description",
    )


class KnowledgeBaseResponse(KnowledgeBaseBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeBaseListResponse(BaseModel):
    items: list[KnowledgeBaseResponse]
    total: int
