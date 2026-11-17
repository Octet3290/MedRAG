import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_knowledge_base_full_crud_lifecycle(auth_client_a: AsyncClient):
    """
    Test complete CRUD lifecycle for Knowledge Base:
    1. Create -> 2. Read -> 3. List -> 4. Update -> 5. Delete -> 6. Verify 404
    """
    # 1. Create Knowledge Base
    payload = {
        "name": "Cardiology Clinical Guidelines",
        "description": "Evidence-based management of heart failure and hypertension.",
    }
    create_res = await auth_client_a.post("/api/v1/knowledge-bases", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["name"] == payload["name"]
    assert created_data["description"] == payload["description"]
    kb_id = created_data["id"]
    assert "owner_id" in created_data

    # 2. Get Knowledge Base by ID
    get_res = await auth_client_a.get(f"/api/v1/knowledge-bases/{kb_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["id"] == kb_id
    assert get_data["name"] == payload["name"]

    # 3. List Knowledge Bases
    list_res = await auth_client_a.get("/api/v1/knowledge-bases")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == kb_id for item in list_data["items"])

    # 4. Update Knowledge Base
    update_payload = {
        "name": "Updated Cardiology Clinical Guidelines 2026",
        "description": "Updated peer-reviewed guidelines.",
    }
    patch_res = await auth_client_a.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        json=update_payload,
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()
    assert patched_data["name"] == update_payload["name"]
    assert patched_data["description"] == update_payload["description"]

    # 5. Delete Knowledge Base
    delete_res = await auth_client_a.delete(f"/api/v1/knowledge-bases/{kb_id}")
    assert delete_res.status_code == 204

    # 6. Verify Knowledge Base is gone
    verify_res = await auth_client_a.get(f"/api/v1/knowledge-bases/{kb_id}")
    assert verify_res.status_code == 404
    assert verify_res.json()["detail"] == "Knowledge base not found"


@pytest.mark.asyncio
async def test_create_knowledge_base_validation(auth_client_a: AsyncClient):
    """Verify input validation rejects empty names."""
    invalid_payload = {"name": "", "description": "No name provided"}
    res = await auth_client_a.post("/api/v1/knowledge-bases", json=invalid_payload)
    assert res.status_code == 422  # Unprocessable Entity
