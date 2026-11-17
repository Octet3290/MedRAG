import time
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.user import User
from app.rag.citations import citation_validator
from app.rag.embeddings import embedding_service
from app.rag.llm import llm_service
from app.rag.prompt import build_chat_prompt, build_reformulation_prompt
from app.repositories.chunk import chunk_repo
from app.repositories.conversation import conversation_repo
from app.schemas.conversation import (
    ChatTurnResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    ConversationUpdate,
    MessageResponse,
    SendMessageRequest,
)
from app.schemas.rag import CitationItem, RetrievalDebugInfo
from app.services.knowledge_base import knowledge_base_service


class ChatService:
    """Service orchestrating multi-turn conversations, query reformulation, and chat persistence."""

    async def create_conversation(
        self,
        db: AsyncSession,
        *,
        kb_id: uuid.UUID,
        obj_in: ConversationCreate,
        current_user: User,
    ) -> Conversation:
        # IDOR protection on knowledge base
        await knowledge_base_service.get_knowledge_base(
            db,
            kb_id=kb_id,
            current_user=current_user,
        )

        title = (
            obj_in.title.strip() if obj_in.title and obj_in.title.strip() else "New Conversation"
        )
        return await conversation_repo.create_conversation(
            db,
            owner_id=current_user.id,
            knowledge_base_id=kb_id,
            title=title,
        )

    async def get_conversation(
        self,
        db: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        current_user: User,
    ) -> ConversationDetailResponse:
        conv = await conversation_repo.get_by_id(db, conversation_id=conversation_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        if conv.owner_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this conversation",
            )

        messages = [
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                citations=[CitationItem(**c) for c in (m.citations or [])],
                model_metadata=m.model_metadata,
                created_at=m.created_at,
            )
            for m in conv.messages
        ]

        return ConversationDetailResponse(
            id=conv.id,
            knowledge_base_id=conv.knowledge_base_id,
            owner_id=conv.owner_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=messages,
        )

    async def list_conversations(
        self,
        db: AsyncSession,
        *,
        kb_id: uuid.UUID,
        current_user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> ConversationListResponse:
        await knowledge_base_service.get_knowledge_base(
            db,
            kb_id=kb_id,
            current_user=current_user,
        )

        rows, total = await conversation_repo.list_by_knowledge_base(
            db,
            owner_id=current_user.id,
            knowledge_base_id=kb_id,
            limit=limit,
            offset=offset,
        )

        items = [
            ConversationSummary(
                id=conv.id,
                knowledge_base_id=conv.knowledge_base_id,
                owner_id=conv.owner_id,
                title=conv.title,
                message_count=count,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
            for conv, count in rows
        ]

        return ConversationListResponse(items=items, total=total)

    async def update_title(
        self,
        db: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        obj_in: ConversationUpdate,
        current_user: User,
    ) -> ConversationSummary:
        conv = await conversation_repo.get_by_id(db, conversation_id=conversation_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        if conv.owner_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )

        updated = await conversation_repo.update_title(db, conversation=conv, title=obj_in.title)
        return ConversationSummary(
            id=updated.id,
            knowledge_base_id=updated.knowledge_base_id,
            owner_id=updated.owner_id,
            title=updated.title,
            message_count=len(updated.messages),
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    async def delete_conversation(
        self,
        db: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        current_user: User,
    ) -> None:
        conv = await conversation_repo.get_by_id(db, conversation_id=conversation_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        if conv.owner_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )

        await conversation_repo.delete(db, conversation=conv)

    async def post_message_and_respond(
        self,
        db: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        request: SendMessageRequest,
        current_user: User,
    ) -> ChatTurnResponse:
        start_time = time.perf_counter()

        # 1. Authorize conversation
        conv = await conversation_repo.get_by_id(db, conversation_id=conversation_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        if conv.owner_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this conversation",
            )

        # 2. Persist User Message
        user_msg = await conversation_repo.add_message(
            db,
            conversation_id=conversation_id,
            role="user",
            content=request.content.strip(),
        )

        # 3. Retrieve prior dialogue turns
        prior_messages = [m for m in conv.messages if m.id != user_msg.id]
        history_dicts = [{"role": m.role, "content": m.content} for m in prior_messages]

        # 4. Contextual Query Reformulation
        standalone_query = request.content.strip()
        if history_dicts:
            ref_sys, ref_user = build_reformulation_prompt(request.content, history_dicts)
            reformulated = await llm_service.generate_answer(ref_sys, ref_user)
            if reformulated and reformulated.strip():
                standalone_query = reformulated.strip()

        # 5. Embed Query and Vector Search in pgvector
        query_vector = await embedding_service.embed_query(standalone_query)
        chunks_with_dist = await chunk_repo.search_similar_chunks(
            db,
            knowledge_base_id=conv.knowledge_base_id,
            query_vector=query_vector,
            top_k=request.top_k,
        )

        top_dist = chunks_with_dist[0][1] if chunks_with_dist else None

        # 6. Build Multi-turn Grounded Prompt
        sys_prompt, user_prompt = build_chat_prompt(
            question=request.content.strip(),
            chunks_with_distance=chunks_with_dist,
            chat_history=history_dicts,
        )

        # 7. LLM Generation
        raw_answer = await llm_service.generate_answer(
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
        )

        # 8. Citation Validation
        verified_citations = citation_validator.validate(
            answer=raw_answer,
            retrieved_chunks=chunks_with_dist,
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        citations_data = [c.model_dump(mode="json") for c in verified_citations]

        # 9. Persist Assistant Message
        assistant_msg = await conversation_repo.add_message(
            db,
            conversation_id=conversation_id,
            role="assistant",
            content=raw_answer,
            citations=citations_data,
            model_metadata={
                "latency_ms": latency_ms,
                "standalone_query": standalone_query,
                "chunks_retrieved": len(chunks_with_dist),
                "top_distance": top_dist,
            },
        )

        # 10. Auto-title conversation if default
        if conv.title == "New Conversation":
            words = request.content.strip().split()
            new_title = " ".join(words[:6])
            if len(new_title) > 60:
                new_title = new_title[:57] + "..."
            await conversation_repo.update_title(db, conversation=conv, title=new_title)

        return ChatTurnResponse(
            user_message=MessageResponse(
                id=user_msg.id,
                conversation_id=user_msg.conversation_id,
                role=user_msg.role,
                content=user_msg.content,
                citations=[],
                model_metadata={},
                created_at=user_msg.created_at,
            ),
            assistant_message=MessageResponse(
                id=assistant_msg.id,
                conversation_id=assistant_msg.conversation_id,
                role=assistant_msg.role,
                content=assistant_msg.content,
                citations=verified_citations,
                model_metadata=assistant_msg.model_metadata,
                created_at=assistant_msg.created_at,
            ),
            standalone_query=standalone_query,
            retrieval_debug=RetrievalDebugInfo(
                chunks_retrieved=len(chunks_with_dist),
                top_distance=top_dist,
                latency_ms=latency_ms,
            ),
        )


chat_service = ChatService()
