import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cross_user_resource_isolation(
    auth_client_a: AsyncClient,
    auth_client_b: AsyncClient,
):
    """
    SECURITY TEST: Insecure Direct Object Reference (IDOR) Defense
    Verify that User B cannot read, update, or delete User A's private Knowledge Base,
    and that User B's list endpoint does not expose User A's resources.
    """
    # 1. User A creates a private Knowledge Base
    payload_a = {
        "name": "User A Private Genomic Records",
        "description": "Confidential patient sequencing data.",
    }
    create_res = await auth_client_a.post("/api/v1/knowledge-bases", json=payload_a)
    assert create_res.status_code == 201
    kb_a_id = create_res.json()["id"]

    # 2. User B attempts to read User A's Knowledge Base by ID -> 403 Forbidden
    read_attempt = await auth_client_b.get(f"/api/v1/knowledge-bases/{kb_a_id}")
    assert read_attempt.status_code == 403
    assert "permission" in read_attempt.json()["detail"].lower()

    # 3. User B attempts to update User A's Knowledge Base -> 403 Forbidden
    update_attempt = await auth_client_b.patch(
        f"/api/v1/knowledge-bases/{kb_a_id}",
        json={"name": "Tampered By User B"},
    )
    assert update_attempt.status_code == 403

    # 4. User B attempts to delete User A's Knowledge Base -> 403 Forbidden
    delete_attempt = await auth_client_b.delete(f"/api/v1/knowledge-bases/{kb_a_id}")
    assert delete_attempt.status_code == 403

    # 5. User B lists their knowledge bases -> User A's record must NOT be present
    list_res = await auth_client_b.get("/api/v1/knowledge-bases")
    assert list_res.status_code == 200
    user_b_items = list_res.json()["items"]
    assert not any(item["id"] == kb_a_id for item in user_b_items)

    # 6. Verify User A can still read and delete their own Knowledge Base
    cleanup_res = await auth_client_a.delete(f"/api/v1/knowledge-bases/{kb_a_id}")
    assert cleanup_res.status_code == 204
