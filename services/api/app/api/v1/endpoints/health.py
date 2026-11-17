from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """
    Service Health Check endpoint.
    Performs active database probe query to verify connectivity.
    """
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unreachable: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        environment=settings.ENVIRONMENT,
        version="0.1.0",
        database=db_status,
    )
