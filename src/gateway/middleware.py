"""中间件注册"""

import time

import structlog
from fastapi import FastAPI, Request, Response

logger = structlog.get_logger(__name__)


async def request_logging_middleware(request: Request, call_next) -> Response:
    """请求日志中间件"""
    start_time = time.time()

    response = await call_next(request)

    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )

    return response


def register_middlewares(app: FastAPI) -> None:
    """注册所有中间件"""
    app.middleware("http")(request_logging_middleware)
