import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.rag.evaluator import DEFAULT_MEDICAL_BENCHMARK, rag_evaluator
from app.schemas.eval import (
    EvaluationReportResponse,
    EvaluationSummaryMetrics,
    RunEvaluationRequest,
    SampleEvaluationResult,
)
from app.schemas.rag import QueryRequest
from app.services.knowledge_base import knowledge_base_service
from app.services.rag import rag_service


class EvaluationService:
    """Service orchestrating RAG precision/recall benchmarks and evaluation metrics."""

    async def run_evaluation(
        self,
        db: AsyncSession,
        *,
        kb_id: uuid.UUID,
        request: RunEvaluationRequest,
        current_user: User,
    ) -> EvaluationReportResponse:
        """
        Execute an automated RAG evaluation benchmark against a Knowledge Base:
        1. Enforces Knowledge Base ownership and authorization.
        2. Evaluates each sample query against vector retrieval and generation.
        3. Computes sample-level Hit@K, MRR, Faithfulness, Relevance, and Citation Accuracy.
        4. Aggregates macro-average metrics into an EvaluationReportResponse.
        """
        # 1. Enforce IDOR protection and verify Knowledge Base exists
        await knowledge_base_service.get_knowledge_base(db, kb_id=kb_id, current_user=current_user)

        samples = request.custom_samples if request.custom_samples else DEFAULT_MEDICAL_BENCHMARK

        sample_results: list[SampleEvaluationResult] = []

        for sample in samples:
            # Execute query and capture retrieved chunks
            query_req = QueryRequest(question=sample.question, top_k=request.top_k)
            query_res, retrieved_chunks = await rag_service.query_with_chunks(
                db,
                kb_id=kb_id,
                request=query_req,
                current_user=current_user,
            )

            # Score sample
            result = rag_evaluator.evaluate_sample(
                sample=sample,
                query_response=query_res,
                retrieved_chunks=retrieved_chunks,
                latency_ms=query_res.retrieval_debug.latency_ms,
            )
            sample_results.append(result)

        total = len(sample_results) or 1
        summary = EvaluationSummaryMetrics(
            total_samples=len(sample_results),
            hit_rate_at_k=round(sum(1 for r in sample_results if r.hit_at_k) / total, 3),
            mrr=round(sum(r.reciprocal_rank for r in sample_results) / total, 3),
            mean_faithfulness=round(sum(r.faithfulness_score for r in sample_results) / total, 3),
            mean_answer_relevance=round(
                sum(r.answer_relevance_score for r in sample_results) / total, 3
            ),
            mean_citation_accuracy=round(
                sum(r.citation_accuracy for r in sample_results) / total, 3
            ),
            mean_latency_ms=round(sum(r.latency_ms for r in sample_results) / total, 2),
        )

        return EvaluationReportResponse(
            knowledge_base_id=kb_id,
            top_k=request.top_k,
            metrics=summary,
            results=sample_results,
        )


evaluation_service = EvaluationService()
