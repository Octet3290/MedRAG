import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.rag import CitationItem, RetrievalDebugInfo


class ConversationCreate(BaseModel):
    """Payload to initialize a new conversation session."""

    title: str | None = Field(
        default=None,
        max_length=255,
        description="Optional title for the conversation session.",
        examples=["Diabetes Management Consultation"],
    )


class ConversationUpdate(BaseModel):
    """Payload to update conversation properties (e.g. rename title)."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="New title for the conversation.",
    )


class MessageResponse(BaseModel):
    """Schema representing a single message within a conversation thread."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str = Field(..., description="Sender role: 'user', 'assistant', or 'system'")
    content: str
    citations: list[CitationItem] | None = None
    model_metadata: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationSummary(BaseModel):
    """Summary of a conversation for list views."""

    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    """Full conversation detail with chronologically ordered message history."""

    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    """Paginated list of user conversations within a knowledge base."""

    items: list[ConversationSummary]
    total: int


class SendMessageRequest(BaseModel):
    """Payload for submitting a user message to an existing conversation."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question or message to the assistant.",
        examples=["What are the renal contraindications for metformin?"],
    )
    top_k: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Number of chunks to retrieve for grounding.",
    )


class ChatTurnResponse(BaseModel):
    """Response containing both the saved user message and the generated assistant response."""

    user_message: MessageResponse
    assistant_message: MessageResponse
    standalone_query: str | None = None
    retrieval_debug: RetrievalDebugInfo
