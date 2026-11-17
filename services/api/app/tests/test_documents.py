import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_document_upload_and_lifecycle(
    auth_client_a: AsyncClient,
    auth_client_b: AsyncClient,
):
    """
    Test document upload, status reporting, list, and cross-user authorization:
    1. User A creates Knowledge Base.
    2. User A uploads a valid document.
    3. User A lists documents in Knowledge Base.
    4. User B attempts to access User A's document -> 403 Forbidden.
    5. User B attempts to upload to User A's Knowledge Base -> 403 Forbidden.
    6. User A deletes document.
    """
    # 1. User A creates Knowledge Base
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Oncology Documentation"},
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    # 2. User A uploads a valid TXT document
    doc_content = (
        "ONCOLOGY CLINICAL SUMMARY 2026\n\n"
        "Immunotherapy combined with targeted radiation demonstrates a 42% improvement "
        "in 5-year survival rates for stage III melanoma."
    )
    files = {"file": ("oncology_summary.txt", doc_content.encode("utf-8"), "text/plain")}
    upload_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload",
        files=files,
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    assert doc_data["original_filename"] == "oncology_summary.txt"
    assert doc_data["status"] == "ready"
    assert doc_data["file_size_bytes"] > 0
    doc_id = doc_data["id"]

    # 3. User A lists documents in Knowledge Base
    list_res = await auth_client_a.get(f"/api/v1/knowledge-bases/{kb_id}/documents")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == doc_id for item in list_data["items"])

    # 4. User B attempts to access User A's document -> 403 Forbidden
    unauthorized_get = await auth_client_b.get(f"/api/v1/documents/{doc_id}")
    assert unauthorized_get.status_code == 403

    # 5. User B attempts to upload to User A's Knowledge Base -> 403 Forbidden
    unauthorized_upload = await auth_client_b.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload",
        files={"file": ("infiltrate.txt", b"Attempted upload to victim KB.", "text/plain")},
    )
    assert unauthorized_upload.status_code == 403

    # 6. User A deletes document
    delete_res = await auth_client_a.delete(f"/api/v1/documents/{doc_id}")
    assert delete_res.status_code == 204

    # 7. Document is gone
    verify_get = await auth_client_a.get(f"/api/v1/documents/{doc_id}")
    assert verify_get.status_code == 404
