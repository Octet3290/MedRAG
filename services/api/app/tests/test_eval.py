import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_evaluation_benchmark_end_to_end(
    auth_client_a: AsyncClient,
):
    """
    Test automated RAG precision/recall benchmark:
    1. Create Knowledge Base.
    2. Upload clinical medical documents (Cardiology & Oncology).
    3. Run evaluation benchmark suite against Knowledge Base.
    4. Assert Hit Rate @ K, MRR, Faithfulness, Relevance, and Citation metrics.
    """
    # 1. Create Knowledge Base
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Clinical Evaluation KB"},
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    # 2. Upload cardiology protocol document
    cardio_content = (
        "CARDIOLOGY CLINICAL PROTOCOL 2026\n\n"
        "Beta-blockers are first-line therapy for rate control in symptomatic atrial fibrillation. "
        "Target resting heart rate should be maintained below 80 beats per minute."
    )
    await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload",
        files={"file": ("cardiology_protocol.txt", cardio_content.encode("utf-8"), "text/plain")},
    )

    # Upload oncology summary document
    onco_content = (
        "ONCOLOGY CLINICAL SUMMARY 2026\n\n"
        "Immunotherapy combined with targeted radiation demonstrates a 42% improvement "
        "in 5-year survival rates for stage III melanoma."
    )
    await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload",
        files={"file": ("oncology_summary.txt", onco_content.encode("utf-8"), "text/plain")},
    )

    # 3. Trigger evaluation benchmark
    eval_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/eval",
        json={"top_k": 4},
    )
    assert eval_res.status_code == 200
    report = eval_res.json()

    assert report["top_k"] == 4
    metrics = report["metrics"]
    assert metrics["total_samples"] == 4
    # Hit rate should be high (> 0.5) because 2 clinical documents and refusal are present
    assert metrics["hit_rate_at_k"] >= 0.5
    assert metrics["mrr"] > 0.0
    assert metrics["mean_faithfulness"] >= 0.75
    assert metrics["mean_latency_ms"] > 0.0

    # Verify per-sample breakdown
    results = report["results"]
    assert len(results) == 4

    # The cardio question must be a hit
    cardio_sample = next(r for r in results if "atrial fibrillation" in r["question"])
    assert cardio_sample["hit_at_k"] is True
    assert cardio_sample["reciprocal_rank"] > 0.0
    assert "beta-blocker" in cardio_sample["generated_answer"].lower()

    # The out-of-domain query (Australia) must be handled with honest refusal
    refusal_sample = next(r for r in results if "Australia" in r["question"])
    assert refusal_sample["faithfulness_score"] == 1.0


@pytest.mark.asyncio
async def test_evaluation_idor_cross_user_isolation(
    auth_client_a: AsyncClient,
    auth_client_b: AsyncClient,
):
    """
    Verify IDOR authorization guard: User B cannot run evaluations on User A's Knowledge Base.
    """
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "User A Private KB"},
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    # User B attempts evaluation on User A's KB -> 403 Forbidden
    eval_res = await auth_client_b.post(
        f"/api/v1/knowledge-bases/{kb_id}/eval",
        json={"top_k": 4},
    )
    assert eval_res.status_code == 403


@pytest.mark.asyncio
async def test_custom_evaluation_samples(
    auth_client_a: AsyncClient,
):
    """
    Verify running evaluation with custom questions instead of default benchmark.
    """
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Custom Eval KB"},
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    content = "Pediatric dosing guidelines specify amoxicillin at 40 mg/kg/day divided twice daily."
    await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload",
        files={"file": ("pediatric_dosing.txt", content.encode("utf-8"), "text/plain")},
    )

    custom_samples = [
        {
            "id": "peds-01",
            "question": "What is the recommended pediatric dosage for amoxicillin?",
            "expected_answer": "40 mg/kg/day divided twice daily.",
            "ground_truth_doc_filename": "pediatric_dosing.txt",
            "ground_truth_page": 1,
            "ground_truth_keywords": ["40 mg/kg/day", "amoxicillin"],
        }
    ]

    eval_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/eval",
        json={"top_k": 3, "custom_samples": custom_samples},
    )
    assert eval_res.status_code == 200
    report = eval_res.json()

    assert report["metrics"]["total_samples"] == 1
    assert report["metrics"]["hit_rate_at_k"] == 1.0
    assert report["metrics"]["mrr"] == 1.0
    assert len(report["results"]) == 1
    assert report["results"][0]["hit_at_k"] is True
