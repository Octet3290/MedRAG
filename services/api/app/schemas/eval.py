import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.schemas.rag import CitationItem


class EvaluationSample(BaseModel):
    """A curated evaluation test case representing a question and ground truth expectations."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    question: str
    expected_answer: str
    ground_truth_doc_filename: str | None = None
    ground_truth_page: int | None = None
    ground_truth_keywords: list[str] = Field(default_factory=list)


class SampleEvaluationResult(BaseModel):
    """Detailed evaluation scores for a single evaluation question."""

    sample_id: str
    question: str
    generated_answer: str
    retrieved_chunks_count: int
    hit_at_k: bool = Field(
        ...,
        description="Whether a ground-truth chunk was found in the top-K retrieved results.",
    )
    reciprocal_rank: float = Field(
        ...,
        description="1 / rank of first relevant chunk in top-K (0.0 if not found).",
    )
    citation_accuracy: float = Field(
        ...,
        description="Proportion of citations matching ground truth sources (0.0 to 1.0).",
    )
    faithfulness_score: float = Field(
        ...,
        description="Proportion of generated answer claims grounded in context (0.0 to 1.0).",
    )
    answer_relevance_score: float = Field(
        ...,
        description="Score reflecting query coverage and expected clinical entities (0.0 to 1.0).",
    )
    latency_ms: float
    citations: list[CitationItem] = Field(default_factory=list)
    retrieved_sources: list[str] = Field(default_factory=list)


class EvaluationSummaryMetrics(BaseModel):
    """Aggregated macro-average metrics across the entire evaluation run."""

    total_samples: int
    hit_rate_at_k: float = Field(
        ...,
        description="Percentage of queries where at least one ground-truth chunk was retrieved.",
    )
    mrr: float = Field(
        ...,
        description="Mean Reciprocal Rank across all queries in the evaluation run.",
    )
    mean_faithfulness: float = Field(
        ...,
        description="Macro-average faithfulness (hallucination defense) score.",
    )
    mean_answer_relevance: float = Field(
        ...,
        description="Macro-average answer relevance score.",
    )
    mean_citation_accuracy: float = Field(
        ...,
        description="Macro-average citation accuracy score.",
    )
    mean_latency_ms: float


class RunEvaluationRequest(BaseModel):
    """Request payload to trigger an automated RAG evaluation benchmark."""

    top_k: int = Field(default=4, ge=1, le=10)
    custom_samples: list[EvaluationSample] | None = Field(
        default=None,
        description="Optional custom test cases. If omitted, standard suite is used.",
    )


class EvaluationReportResponse(BaseModel):
    """Complete evaluation report response payload."""

    knowledge_base_id: uuid.UUID
    top_k: int
    metrics: EvaluationSummaryMetrics
    results: list[SampleEvaluationResult]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
