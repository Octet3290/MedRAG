import os
import uuid

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.workers.ingestion import process_document_task


@pytest.mark.asyncio
async def test_upload_document_background_flow(auth_client_a: AsyncClient):
    """
    Test background ingestion workflow:
    1. Upload document with background=True.
    2. Verify immediate response returns status='processing'.
    3. Execute / complete process_document_task worker.
    4. Verify document status transitions to 'ready' with indexed chunks in pgvector.
    """
    # 1. Create Knowledge Base
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Cardiology Knowledge Base"},
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    # 2. Upload document with background=True
    doc_content = (
        "CARDIOLOGY CLINICAL PROTOCOL 2026\n\n"
        "Beta-blockers are first-line therapy for rate control in symptomatic atrial fibrillation. "
        "Target resting heart rate should be maintained below 80 beats per minute."
    )
    files = {"file": ("cardiology_protocol.txt", doc_content.encode("utf-8"), "text/plain")}
    upload_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload?background=true",
        files=files,
    )
    assert upload_res.status_code == 201
    data = upload_res.json()
    assert data["status"] == "processing"
    assert data["original_filename"] == "cardiology_protocol.txt"
    doc_id = uuid.UUID(data["id"])

    # 3. Explicitly execute process_document_task to ensure worker lifecycle completes
    await process_document_task(doc_id)

    # 4. Fetch document and verify status is 'ready'
    doc_res = await auth_client_a.get(f"/api/v1/documents/{doc_id}")
    assert doc_res.status_code == 200
    doc_data = doc_res.json()
    assert doc_data["status"] == "ready"
    assert doc_data["error_summary"] is None

    # 5. Verify chunks were stored in pgvector
    chunks_res = await auth_client_a.get(f"/api/v1/documents/{doc_id}/chunks")
    assert chunks_res.status_code == 200
    chunks_data = chunks_res.json()
    assert chunks_data["total"] >= 1
    assert "Beta-blockers" in chunks_data["items"][0]["text_content"]


@pytest.mark.asyncio
async def test_document_background_failure_handling(auth_client_a: AsyncClient):
    """
    Test failure handling during background ingestion:
    1. Upload document with background=True.
    2. Intentionally delete physical file from disk.
    3. Run worker task.
    4. Verify document status becomes 'failed' and error_summary is captured.
    """
    from app.core.database import AsyncSessionLocal
    from app.repositories.document import document_repo

    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Failure Handling KB"},
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    content = "Physical file test content that will be removed before re-indexing."
    files = {"file": ("corrupt_target.txt", content.encode("utf-8"), "text/plain")}
    upload_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload?background=true",
        files=files,
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = uuid.UUID(doc_data["id"])

    # Retrieve internal storage key from database session
    async with AsyncSessionLocal() as session:
        db_doc = await document_repo.get_by_id(session, doc_id=doc_id)
        assert db_doc is not None
        storage_key = db_doc.storage_key

    # Delete physical file from disk to simulate storage error
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    file_path = os.path.join(upload_dir, storage_key)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Run worker task
    await process_document_task(doc_id)

    # Fetch document and verify failed state
    doc_res = await auth_client_a.get(f"/api/v1/documents/{doc_id}")
    assert doc_res.status_code == 200
    updated = doc_res.json()
    assert updated["status"] == "failed"
    assert updated["error_summary"] is not None
    assert "not found" in updated["error_summary"].lower()


@pytest.mark.asyncio
async def test_reindex_document_background_flow(auth_client_a: AsyncClient):
    """
    Test asynchronous reindexing flow:
    1. Upload document synchronously (ready).
    2. Call reindex with background=True -> immediate status 'processing'.
    3. Execute worker task -> document status transitions back to 'ready'.
    """
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Reindex Test KB"},
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    content = "INITIAL CLINICAL NOTES: Patient showed tolerance to first dosage."
    files = {"file": ("reindex_target.txt", content.encode("utf-8"), "text/plain")}
    upload_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload",
        files=files,
    )
    assert upload_res.status_code == 201
    doc_id = uuid.UUID(upload_res.json()["id"])
    assert upload_res.json()["status"] == "ready"

    # Trigger reindex with background=true
    reindex_res = await auth_client_a.post(f"/api/v1/documents/{doc_id}/reindex?background=true")
    assert reindex_res.status_code == 200
    assert reindex_res.json()["status"] == "processing"

    # Worker executes
    await process_document_task(doc_id)

    # Verify status is back to ready
    doc_res = await auth_client_a.get(f"/api/v1/documents/{doc_id}")
    assert doc_res.status_code == 200
    assert doc_res.json()["status"] == "ready"
