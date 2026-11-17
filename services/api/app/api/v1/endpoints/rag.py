import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.rag import QueryRequest, QueryResponse
from app.security.deps import get_current_user
from app.services.rag import rag_service

router = APIRouter(prefix="/knowledge-bases", tags=["RAG & Query"])


@router.post(
    "/{kb_id}/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a question to a Knowledge Base and receive a grounded answer with citations",
)
async def query_knowledge_base(
    kb_id: uuid.UUID,
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryResponse:
    """
    Execute a Grounded RAG query against the indexed documents of a specific Knowledge Base.

    - **Resource Isolation**: Enforces user ownership of the Knowledge Base.
    - **Vector Search**: Embeds question and queries pgvector with cosine distance.
    - **Grounding**: Instructs LLM to answer only using retrieved text passages.
    - **Citations**: Returns verified source citations with document title and page number.
    """
    return await rag_service.query_knowledge_base(
        db,
        kb_id=kb_id,
        request=request,
        current_user=current_user,
    )
