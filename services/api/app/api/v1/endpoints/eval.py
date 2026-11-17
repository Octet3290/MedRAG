import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.eval import EvaluationReportResponse, RunEvaluationRequest
from app.security.deps import get_current_user
from app.services.eval import evaluation_service

router = APIRouter(tags=["Evaluation"])


@router.post(
    "/knowledge-bases/{kb_id}/eval",
    response_model=EvaluationReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Run automated RAG evaluation benchmark",
)
async def run_evaluation_benchmark(
    kb_id: uuid.UUID,
    request: RunEvaluationRequest = RunEvaluationRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluationReportResponse:
    """
    Execute an automated RAG precision/recall benchmark against a Knowledge Base.
    Computes Hit Rate @ K, MRR, Faithfulness, Relevance, Citation Accuracy, and Latency.
    """
    return await evaluation_service.run_evaluation(
        db,
        kb_id=kb_id,
        request=request,
        current_user=current_user,
    )
