import re

from app.models.chunk import DocumentChunk
from app.schemas.eval import EvaluationSample, SampleEvaluationResult
from app.schemas.rag import CitationItem, QueryResponse

DEFAULT_MEDICAL_BENCHMARK: list[EvaluationSample] = [
    EvaluationSample(
        id="cardio-01",
        question=(
            "What is the recommended first-line therapy for rate control in "
            "atrial fibrillation and what is the target heart rate?"
        ),
        expected_answer=(
            "Beta-blockers are first-line therapy for rate control in symptomatic "
            "atrial fibrillation, with a target resting heart rate maintained below "
            "80 beats per minute."
        ),
        ground_truth_doc_filename="cardiology_protocol.txt",
        ground_truth_page=1,
        ground_truth_keywords=["beta-blocker", "atrial fibrillation", "80"],
    ),
    EvaluationSample(
        id="onco-01",
        question=(
            "What improvement in 5-year survival rate was observed with immunotherapy "
            "and targeted radiation for stage III melanoma?"
        ),
        expected_answer=(
            "Immunotherapy combined with targeted radiation demonstrates a 42% "
            "improvement in 5-year survival rates for stage III melanoma."
        ),
        ground_truth_doc_filename="oncology_summary.txt",
        ground_truth_page=1,
        ground_truth_keywords=["42%", "melanoma", "immunotherapy"],
    ),
    EvaluationSample(
        id="endo-01",
        question="What are the major contraindications for metformin administration?",
        expected_answer=(
            "Metformin is contraindicated in severe renal impairment and acute metabolic acidosis."
        ),
        ground_truth_doc_filename="metformin_guidelines.txt",
        ground_truth_page=1,
        ground_truth_keywords=["renal impairment", "contraindicated"],
    ),
    EvaluationSample(
        id="refusal-01",
        question="What is the capital city of Australia?",
        expected_answer=(
            "I do not have sufficient information in the provided documentation to answer."
        ),
        ground_truth_doc_filename=None,
        ground_truth_page=None,
        ground_truth_keywords=["not have sufficient information"],
    ),
]


class RAGEvaluator:
    """Core evaluation engine calculating retrieval and generation metrics."""

    def evaluate_retrieval(
        self,
        retrieved_chunks: list[DocumentChunk],
        sample: EvaluationSample,
    ) -> tuple[bool, float, list[str]]:
        """
        Compute Hit Rate @ K and Reciprocal Rank (MRR component):
        - Hit@K = True if a relevant chunk appears in top-K.
        - Reciprocal Rank = 1 / (rank of first relevant chunk) or 0.0 if not found.
        """
        retrieved_sources: list[str] = []
        for c in retrieved_chunks:
            fname = c.document.original_filename if c.document else "unknown"
            retrieved_sources.append(f"{fname}:p{c.page_number or 1}")

        # Out-of-domain refusal test: expected to NOT match any ground truth document
        if not sample.ground_truth_doc_filename and not sample.ground_truth_keywords:
            return True, 1.0, retrieved_sources

        # Match against ground-truth document name or key clinical entities
        first_match_rank: int | None = None
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            chunk_doc_name = chunk.document.original_filename if chunk.document else ""
            matches_doc = (
                sample.ground_truth_doc_filename
                and sample.ground_truth_doc_filename.lower() in chunk_doc_name.lower()
            )
            matches_keywords = False
            if sample.ground_truth_keywords:
                chunk_lower = chunk.text_content.lower()
                matches_keywords = any(
                    kw.lower() in chunk_lower for kw in sample.ground_truth_keywords
                )

            if matches_doc or matches_keywords:
                first_match_rank = idx
                break

        if first_match_rank is not None:
            return True, 1.0 / first_match_rank, retrieved_sources

        return False, 0.0, retrieved_sources

    def evaluate_faithfulness(
        self,
        answer: str,
        retrieved_chunks: list[DocumentChunk],
    ) -> float:
        """
        Evaluate Groundedness / Faithfulness:
        Verifies that claims made in the generated answer are supported by retrieved context.
        Refusal statements are considered 100% faithful.
        """
        # Honest refusal answers are intrinsically 100% faithful
        refusal_markers = [
            "do not have sufficient information",
            "insufficient documentation",
            "cannot answer",
        ]
        if any(marker in answer.lower() for marker in refusal_markers):
            return 1.0

        if not retrieved_chunks:
            return 0.0

        # Concatenate context for verification
        combined_context = " ".join(c.text_content.lower() for c in retrieved_chunks)

        # Split answer into sentence claims
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", answer)
            if len(s.strip()) > 10 and not s.strip().startswith("[Source:")
        ]
        if not sentences:
            return 1.0

        supported_count = 0
        for sent in sentences:
            words = [
                w.lower()
                for w in re.findall(r"\b[a-zA-Z0-9-]+\b", sent)
                if len(w) > 3
                and w.lower()
                not in {
                    "this",
                    "that",
                    "with",
                    "from",
                    "have",
                    "indicated",
                    "recommended",
                    "according",
                }
            ]
            if not words:
                supported_count += 1
                continue

            # Check if at least 50% of the sentence's key entities/words appear in context
            matched_words = [w for w in words if w in combined_context]
            if len(matched_words) / len(words) >= 0.4:
                supported_count += 1

        return round(supported_count / len(sentences), 2)

    def evaluate_answer_relevance(
        self,
        question: str,
        answer: str,
        sample: EvaluationSample,
    ) -> float:
        """
        Evaluate Answer Relevance:
        Measures whether the generated answer addressed the question and included key facts.
        """
        refusal_markers = ["not have sufficient information", "cannot answer"]
        is_refusal_sample = any(
            marker in sample.expected_answer.lower() for marker in refusal_markers
        )

        if is_refusal_sample:
            if any(marker in answer.lower() for marker in refusal_markers):
                return 1.0
            return 0.0

        # Check coverage of ground-truth keywords in generated answer
        if not sample.ground_truth_keywords:
            return 1.0

        ans_lower = answer.lower()
        matched = sum(1 for kw in sample.ground_truth_keywords if kw.lower() in ans_lower)
        return round(matched / len(sample.ground_truth_keywords), 2)

    def evaluate_citation_accuracy(
        self,
        citations: list[CitationItem],
        sample: EvaluationSample,
    ) -> float:
        """
        Evaluate Citation Accuracy:
        - For refusal queries: accurate if no citations are fabricated.
        - For documented queries: accurate if citations match ground truth document/page.
        """
        if not sample.ground_truth_doc_filename:
            return 1.0 if len(citations) == 0 else 0.0

        if not citations:
            return 0.0

        matches = 0
        gt_doc = sample.ground_truth_doc_filename.lower()
        for cit in citations:
            if gt_doc in cit.document_title.lower():
                if sample.ground_truth_page is None or cit.page_number == sample.ground_truth_page:
                    matches += 1

        return round(min(1.0, matches / max(1, len(citations))), 2)

    def evaluate_sample(
        self,
        sample: EvaluationSample,
        query_response: QueryResponse,
        retrieved_chunks: list[DocumentChunk],
        latency_ms: float,
    ) -> SampleEvaluationResult:
        """Score an individual evaluation sample across all retrieval and generation metrics."""
        hit_at_k, reciprocal_rank, retrieved_sources = self.evaluate_retrieval(
            retrieved_chunks, sample
        )
        faithfulness = self.evaluate_faithfulness(query_response.answer, retrieved_chunks)
        relevance = self.evaluate_answer_relevance(sample.question, query_response.answer, sample)
        citation_acc = self.evaluate_citation_accuracy(query_response.citations, sample)

        return SampleEvaluationResult(
            sample_id=sample.id,
            question=sample.question,
            generated_answer=query_response.answer,
            retrieved_chunks_count=len(retrieved_chunks),
            hit_at_k=hit_at_k,
            reciprocal_rank=round(reciprocal_rank, 3),
            citation_accuracy=citation_acc,
            faithfulness_score=faithfulness,
            answer_relevance_score=relevance,
            latency_ms=round(latency_ms, 2),
            citations=query_response.citations,
            retrieved_sources=retrieved_sources,
        )


rag_evaluator = RAGEvaluator()
