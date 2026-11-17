import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rag_query_grounded_answer_and_citations(auth_client_a: AsyncClient):
    """
    Test Milestone 6 Core Vertical Slice:
    1. Upload document into Knowledge Base.
    2. Submit question.
    3. Verify grounded answer contains answer from document.
    4. Verify verified citations contain document title, page number, and chunk ID.
    5. Verify debug retrieval metadata.
    """
    # 1. Create Knowledge Base
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Cardiology & Metabolic Protocols"},
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    # 2. Upload Document
    doc_text = (
        "AMERICAN DIABETES ASSOCIATION CLINICAL GUIDELINES\n\n"
        "Metformin is the initial first-line pharmacologic agent for type 2 diabetes.\n\n"
        "Empagliflozin and Dapagliflozin provide demonstrated renal protection "
        "and reduce cardiovascular mortality in patients with chronic kidney disease."
    )
    files = {"file": ("ada_guidelines.txt", doc_text.encode("utf-8"), "text/plain")}
    upload_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload",
        files=files,
    )
    assert upload_res.status_code == 201

    # 3. Ask grounded question
    query_payload = {
        "question": "What is the initial first-line pharmacologic agent for type 2 diabetes?",
        "top_k": 3,
    }
    query_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/query",
        json=query_payload,
    )
    assert query_res.status_code == 200
    data = query_res.json()

    # 4. Verify Answer & Citations
    assert "Metformin" in data["answer"]
    assert len(data["citations"]) >= 1

    first_citation = data["citations"][0]
    assert "ada_guidelines" in first_citation["document_title"]
    assert first_citation["page_number"] == 1
    assert uuid.UUID(first_citation["chunk_id"])
    assert "Metformin" in first_citation["excerpt"]

    # 5. Verify Retrieval Debug Info
    debug_info = data["retrieval_debug"]
    assert debug_info["chunks_retrieved"] >= 1
    assert debug_info["latency_ms"] >= 0.0


@pytest.mark.asyncio
async def test_rag_query_honest_refusal_for_unrelated_topic(auth_client_a: AsyncClient):
    """Verify that questions outside the context return a clear refusal with zero citations."""
    # 1. Create Knowledge Base
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Neurology Archive"},
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    # 2. Upload Document
    doc_text = (
        "ALZHEIMER DISEASE PROTOCOL\n\n"
        "Donepezil and Memantine are standard therapies for mild to moderate dementia."
    )
    files = {"file": ("neuro_guide.txt", doc_text.encode("utf-8"), "text/plain")}
    upload_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload",
        files=files,
    )
    assert upload_res.status_code == 201

    # 3. Ask question completely unrelated to the knowledge base
    query_payload = {
        "question": "What are the orbital mechanics and fuel requirements for Mars landing?",
        "top_k": 3,
    }
    query_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/query",
        json=query_payload,
    )
    assert query_res.status_code == 200
    data = query_res.json()

    assert "cannot answer this question based on the provided documents" in data["answer"]
    assert len(data["citations"]) == 0


@pytest.mark.asyncio
async def test_rag_query_idor_cross_user_isolation(
    auth_client_a: AsyncClient,
    auth_client_b: AsyncClient,
):
    """
    Verify that User B cannot execute RAG queries against User A's Knowledge Base (IDOR defense).
    """
    # 1. User A creates Knowledge Base
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Confidential Clinical Trials"},
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    # 2. User B tries to query User A's Knowledge Base
    query_res = await auth_client_b.post(
        f"/api/v1/knowledge-bases/{kb_id}/query",
        json={"question": "What are the trial outcomes?"},
    )
    assert query_res.status_code in (403, 404)


@pytest.mark.asyncio
async def test_rag_query_input_validation(auth_client_a: AsyncClient):
    """Verify that invalid questions (too short or empty) are rejected with 422."""
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Validation Test KB"},
    )
    kb_id = kb_res.json()["id"]

    # Too short question
    res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/query",
        json={"question": "Hi"},
    )
    assert res.status_code == 422
