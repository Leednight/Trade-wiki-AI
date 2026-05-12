"""API Gateway - 路由注册"""

from fastapi import APIRouter

from src.gateway.middleware import register_middlewares

api_router = APIRouter(prefix="/api")


@api_router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": "0.1.0",
    }


# TODO: Phase 1 注册子路由
# from src.feishu.bot import feishu_router
# api_router.include_router(feishu_router, prefix="/feishu", tags=["feishu"])

# from src.knowledge.store.vector import knowledge_router
# api_router.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])

# from src.teaching.strategy_card import strategy_router
# api_router.include_router(strategy_router, prefix="/strategy", tags=["strategy"])
