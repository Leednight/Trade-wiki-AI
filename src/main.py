"""FastAPI 应用入口"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from src.common.logger import setup_logging
from src.config import get_settings
from src.gateway.router import api_router
from src.gateway.middleware import register_middlewares

logger = structlog.get_logger(__name__)

settings = get_settings()

# 初始化日志
setup_logging(settings.app.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 启动与关闭"""
    logger.info("trade_wiki_ai_starting", version="0.1.0")

    # TODO: 初始化各服务组件
    # - ChromaDB 连接
    # - SQLite 连接
    # - Ollama 健康检查
    # - 向量模型加载

    yield

    # TODO: 清理资源
    logger.info("trade_wiki_ai_stopping")


app = FastAPI(
    title="Trade-Wiki-AI",
    description="可成长的个人交易知识助手",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.app.debug,
)

# 注册路由
app.include_router(api_router)

# 注册中间件
register_middlewares(app)


@app.get("/")
async def root():
    return {
        "name": "Trade-Wiki-AI",
        "version": "0.1.0",
        "status": "running",
    }
