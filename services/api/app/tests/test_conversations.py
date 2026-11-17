import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_conversation_crud_lifecycle(auth_client_a: AsyncClient):
    """Test conversation creation, listing, title updating, and deletion."""
    # 1. Create Knowledge Base
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Endocrinology Clinical Protocols"},
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    # 2. Create Conversation
    conv_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/conversations",
        json={"title": "Metformin Clinical Review"},
    )
    assert conv_res.status_code == 201
    conv_data = conv_res.json()
    conv_id = conv_data["id"]
    assert conv_data["title"] == "Metformin Clinical Review"
    assert len(conv_data["messages"]) == 0

    # 3. List Conversations
    list_res = await auth_client_a.get(f"/api/v1/knowledge-bases/{kb_id}/conversations")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1
    assert any(c["id"] == conv_id for c in list_res.json()["items"])

    # 4. Rename Conversation Title
    patch_res = await auth_client_a.patch(
        f"/api/v1/conversations/{conv_id}",
        json={"title": "Updated Endocrinology Review"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Updated Endocrinology Review"

    # 5. Delete Conversation
    del_res = await auth_client_a.delete(f"/api/v1/conversations/{conv_id}")
    assert del_res.status_code == 204

    # Verify deleted
    get_res = await auth_client_a.get(f"/api/v1/conversations/{conv_id}")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_multi_turn_chat_and_query_reformulation(auth_client_a: AsyncClient):
    """
    Test Milestone 7 Core Multi-Turn Flow:
    1. Upload document into Knowledge Base.
    2. Start conversation session.
    3. Turn 1: User asks initial question -> Assistant answers with citations.
    4. Turn 2: User asks follow-up with ambiguous pronoun ('its contraindications') ->
       System performs query reformulation and returns grounded answer with citations.
    5. Verify full persistent message history in PostgreSQL.
    """
    # 1. Create Knowledge Base
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Pharmacology Reference"},
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    # 2. Upload Document
    doc_text = (
        "METFORMIN CLINICAL PHARMACOLOGY SUMMARY\n\n"
        "Metformin hydrochloride is indicated for the treatment of type 2 diabetes mellitus.\n\n"
        "Contraindications include severe renal impairment (estimated GFR below 30 mL/min), "
        "acute metabolic acidosis, and hypersensitivity."
    )
    files = {"file": ("metformin_guide.txt", doc_text.encode("utf-8"), "text/plain")}
    upload_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/upload",
        files=files,
    )
    assert upload_res.status_code == 201

    # 3. Create Conversation
    conv_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/conversations",
        json={"title": None},  # Test auto-title generation
    )
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    # 4. Turn 1: Initial Question
    turn1_res = await auth_client_a.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "What is metformin hydrochloride indicated for?"},
    )
    assert turn1_res.status_code == 200
    t1_data = turn1_res.json()
    assert t1_data["user_message"]["role"] == "user"
    assert "indicated" in t1_data["assistant_message"]["content"]
    assert len(t1_data["assistant_message"]["citations"]) >= 1

    # 5. Turn 2: Follow-up Question with Pronoun ("its contraindications")
    turn2_res = await auth_client_a.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "What are its main contraindications?"},
    )
    assert turn2_res.status_code == 200
    t2_data = turn2_res.json()
    # Check that standalone_query incorporated context
    assert "metformin" in t2_data["standalone_query"].lower()
    assert "renal impairment" in t2_data["assistant_message"]["content"].lower()
    assert len(t2_data["assistant_message"]["citations"]) >= 1

    # 6. Verify Persistent Conversation Detail
    detail_res = await auth_client_a.get(f"/api/v1/conversations/{conv_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    # 2 user messages + 2 assistant messages = 4 messages total
    assert len(detail["messages"]) == 4
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][1]["role"] == "assistant"
    assert detail["messages"][2]["role"] == "user"
    assert detail["messages"][3]["role"] == "assistant"


@pytest.mark.asyncio
async def test_conversation_idor_cross_user_isolation(
    auth_client_a: AsyncClient,
    auth_client_b: AsyncClient,
):
    """Verify that User B cannot access or send messages to User A's conversation."""
    # 1. User A creates Knowledge Base & Conversation
    kb_res = await auth_client_a.post(
        "/api/v1/knowledge-bases",
        json={"name": "Private Oncology Records"},
    )
    kb_id = kb_res.json()["id"]

    conv_res = await auth_client_a.post(
        f"/api/v1/knowledge-bases/{kb_id}/conversations",
        json={"title": "Confidential Consultation"},
    )
    conv_id = conv_res.json()["id"]

    # 2. User B tries to view User A's conversation
    get_res = await auth_client_b.get(f"/api/v1/conversations/{conv_id}")
    assert get_res.status_code in (403, 404)

    # 3. User B tries to post a message into User A's conversation
    msg_res = await auth_client_b.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Attempting unauthorized message injection"},
    )
    assert msg_res.status_code in (403, 404)
