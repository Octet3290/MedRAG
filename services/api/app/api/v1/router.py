from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    conversations,
    documents,
    eval,
    health,
    knowledge_bases,
    rag,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(knowledge_bases.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(rag.router)
api_v1_router.include_router(conversations.router)
api_v1_router.include_router(eval.router)
