import uuid

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    """Payload for submitting a grounded question to a knowledge base."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The question to ask against the documents in the knowledge base.",
        examples=["What is the recommended first-line therapy for type 2 diabetes?"],
    )
    top_k: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Number of relevant chunks to retrieve for context.",
    )
    similarity_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity required (between 0.0 and 1.0).",
    )


class CitationItem(BaseModel):
    """A verified source citation matching a retrieved chunk."""

    document_id: uuid.UUID
    document_title: str
    page_number: int | None = None
    chunk_id: uuid.UUID
    excerpt: str

    model_config = ConfigDict(from_attributes=True)


class RetrievalDebugInfo(BaseModel):
    """Metadata detailing the retrieval and generation performance."""

    chunks_retrieved: int
    top_distance: float | None = None
    latency_ms: float


class QueryResponse(BaseModel):
    """Grounded RAG answer with verified citations and debug metrics."""

    answer: str
    citations: list[CitationItem]
    retrieval_debug: RetrievalDebugInfo
