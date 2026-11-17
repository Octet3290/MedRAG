import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk
from app.models.user import User
from app.rag.citations import citation_validator
from app.rag.embeddings import embedding_service
from app.rag.llm import llm_service
from app.rag.prompt import build_rag_prompt
from app.repositories.chunk import chunk_repo
from app.schemas.rag import QueryRequest, QueryResponse, RetrievalDebugInfo
from app.services.knowledge_base import knowledge_base_service


class RAGService:
    """
    Orchestration service for the Grounded Retrieval-Augmented Generation pipeline.
    Coordinates query embedding, pgvector retrieval, prompt construction, LLM generation,
    and post-generation citation validation.
    """

    async def query_with_chunks(
        self,
        db: AsyncSession,
        *,
        kb_id: uuid.UUID,
        request: QueryRequest,
        current_user: User,
    ) -> tuple[QueryResponse, list[DocumentChunk]]:
        start_time = time.perf_counter()

        # 1. Resource-level authorization & existence check (IDOR guard)
        await knowledge_base_service.get_knowledge_base(
            db,
            kb_id=kb_id,
            current_user=current_user,
        )

        # 2. Embed user question into high-dimensional vector space
        query_vector = await embedding_service.embed_query(request.question)

        # 3. Retrieve top-k nearest semantic chunks via pgvector cosine distance (<=>)
        chunks_with_dist = await chunk_repo.search_similar_chunks(
            db,
            knowledge_base_id=kb_id,
            query_vector=query_vector,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )

        top_dist = chunks_with_dist[0][1] if chunks_with_dist else None

        # 4. If no indexed chunks are found, respond with honest refusal immediately
        if not chunks_with_dist:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            res = QueryResponse(
                answer="I cannot answer this question based on the provided documents.",
                citations=[],
                retrieval_debug=RetrievalDebugInfo(
                    chunks_retrieved=0,
                    top_distance=None,
                    latency_ms=latency_ms,
                ),
            )
            return res, []

        # 5. Construct grounded context block and system instructions
        system_prompt, user_prompt = build_rag_prompt(
            question=request.question,
            chunks_with_distance=chunks_with_dist,
        )

        # 6. LLM Completion (MockLLMProvider or OpenAILLMProvider)
        raw_answer = await llm_service.generate_answer(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # 7. Post-generation citation validation & hallucination guard
        verified_citations = citation_validator.validate(
            answer=raw_answer,
            retrieved_chunks=chunks_with_dist,
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response = QueryResponse(
            answer=raw_answer,
            citations=verified_citations,
            retrieval_debug=RetrievalDebugInfo(
                chunks_retrieved=len(chunks_with_dist),
                top_distance=top_dist,
                latency_ms=latency_ms,
            ),
        )
        chunks = [c for c, _ in chunks_with_dist]
        return response, chunks

    async def query_knowledge_base(
        self,
        db: AsyncSession,
        *,
        kb_id: uuid.UUID,
        request: QueryRequest,
        current_user: User,
    ) -> QueryResponse:
        response, _ = await self.query_with_chunks(
            db,
            kb_id=kb_id,
            request=request,
            current_user=current_user,
        )
        return response


rag_service = RAGService()
