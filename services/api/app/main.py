import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import get_db
from app.schemas.health import HealthResponse

if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager for startup and shutdown events.
    """
    # Startup logic
    yield
    # Shutdown logic


def create_application() -> FastAPI:
    """Application factory for MedRAG FastAPI backend."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="Production-grade AI Knowledge Assistant with verifiable citations.",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if settings.DEBUG else None,
        docs_url=f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
        redoc_url=f"{settings.API_V1_PREFIX}/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root health probe (standard for container orchestrators and load balancers)
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def root_health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
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

    # Versioned API Router
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_application()
