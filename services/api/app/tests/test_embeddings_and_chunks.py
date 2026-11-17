import uuid

import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.rag.embeddings import embedding_service
from app.repositories.chunk import chunk_repo


@pytest.mark.asyncio
async def test_chunking_embeddings_and_pgvector_search(auth_client_a: AsyncClient):
    """
    Test Milestone 5 integration:
    1. Upload document -> Chunks + Embeddings generated.
    2. Inspect chunks via API.
    3. Perform pgvector similarity search.
    4. Re-index document and verify idempotency (no duplicate chunks).
    """
    # 1. Create Knowledge Base
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Endocrinology Research"},
    )
    assert kb_res.status_code == 201
    kb_id = uuid.UUID(kb_res.json()["id"])

    # 2. Upload Document
    doc_text = (
        "DIABETES MELLITUS TYPE 2 CLINICAL PROTOCOL\n\n"
        "Metformin remains the optimal first-line pharmacotherapy for type 2 diabetes.\n\n"
        "GLP-1 receptor agonists are strongly recommended for patients with concurrent "
        "atherosclerotic cardiovascular disease."
    )
    files = {"file": ("diabetes_protocol.txt", doc_text.encode("utf-8"), "text/plain")}
    upload_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload",
        files=files,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 3. Inspect chunks via API
    chunks_res = await auth_client_a.get(f"/api/v1/documents/{doc_id}/chunks")
    assert chunks_res.status_code == 200
    chunks_data = chunks_res.json()
    assert chunks_data["total"] >= 1
    initial_chunk_count = chunks_data["total"]
    first_chunk = chunks_data["items"][0]
    assert first_chunk["page_number"] == 1
    assert "DIABETES" in first_chunk["text_content"]

    # 4. Perform vector similarity search directly with pgvector
    async with AsyncSessionLocal() as session:
        query_vector = await embedding_service.embed_query("metformin first-line therapy")
        results = await chunk_repo.search_similar_chunks(
            session,
            knowledge_base_id=kb_id,
            query_vector=query_vector,
            top_k=3,
        )
        assert len(results) >= 1
        top_chunk, distance = results[0]
        # Distance should be a float >= 0.0
        assert isinstance(distance, float)
        assert distance >= 0.0
        assert top_chunk.document_id == uuid.UUID(doc_id)

    # 5. Test Idempotent Re-indexing
    reindex_res = await auth_client_a.post(f"/api/v1/documents/{doc_id}/reindex")
    assert reindex_res.status_code == 200
    assert reindex_res.json()["status"] == "ready"

    # Verify chunk count didn't double
    verify_chunks = await auth_client_a.get(f"/api/v1/documents/{doc_id}/chunks")
    assert verify_chunks.json()["total"] == initial_chunk_count
