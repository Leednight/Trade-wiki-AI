"""Agent 编排器 - 消息处理的核心调度中心"""

import time
import structlog

from src.config.models import (
    MessageRequest, MessageResponse, RoutingDecision,
    PrivacyLevel, RoutingTarget, MessageSource,
)
from src.agent.router import AgentRouter
from src.agent.context import ContextManager
from src.agent.cache import SemanticCache
from src.agent.tools import ToolRegistry
from src.models.local_client import LocalModelClient
from src.models.cloud_client import CloudModelClient
from src.models.provider import ProviderRouter
from src.privacy.detector import PrivacyDetector
from src.privacy.sanitizer import DataSanitizer
from src.privacy.restore import DataRestorer
from src.common.utils import generate_id

logger = structlog.get_logger(__name__)


class AgentOrchestrator:
    """Agent 编排器 - 所有消息流经此处"""

    def __init__(self):
        # 初始化各组件
        self.local_model = LocalModelClient()
        self.cloud_model = CloudModelClient()
        self.privacy_detector = PrivacyDetector(local_model=self.local_model)
        self.sanitizer = DataSanitizer()
        self.restorer = DataRestorer()
        self.provider_router = ProviderRouter()

        self.router = AgentRouter(
            local_model=self.local_model,
            privacy_detector=self.privacy_detector,
        )
        self.context_manager = ContextManager()
        self.cache = SemanticCache()
        self.tools = ToolRegistry()

    async def handle_message(self, request: MessageRequest) -> MessageResponse:
        """
        处理用户消息的主入口

        流程: 缓存检查 → 路由决策 → 隐私检测 → 模型调用 → 返回
        """
        start_time = time.time()
        conversation_id = generate_id("conv")

        try:
            # 1. 语义缓存检查
            cached_answer = await self.cache.get(request.content)
            if cached_answer:
                self.context_manager.add_message(request.user_id, "user", request.content)
                self.context_manager.add_message(request.user_id, "assistant", cached_answer)
                return MessageResponse(
                    content=cached_answer,
                    source=MessageSource.CACHE,
                    latency_ms=int((time.time() - start_time) * 1000),
                    conversation_id=conversation_id,
                )

            # 2. 路由决策
            decision = await self.router.route(request.content)

            # 3. 根据路由目标分发
            if decision.target == RoutingTarget.LOCAL:
                response = await self._handle_local(request, decision)
            elif decision.target == RoutingTarget.CLOUD:
                response = await self._handle_cloud(request, decision)
            elif decision.target == RoutingTarget.HYBRID:
                response = await self._handle_hybrid(request, decision)
            else:
                response = await self._handle_local(request, decision)

            # 4. 记录对话历史
            self.context_manager.add_message(request.user_id, "user", request.content)
            self.context_manager.add_message(request.user_id, "assistant", response.content)

            # 5. 更新缓存
            await self.cache.set(request.content, response.content, source=response.source.value)

            # 6. 填充元数据
            response.latency_ms = int((time.time() - start_time) * 1000)
            response.privacy_level = decision.privacy_level
            response.conversation_id = conversation_id

            logger.info(
                "message_handled",
                intent=decision.intent,
                target=decision.target.value,
                source=response.source.value,
                latency_ms=response.latency_ms,
            )

            return response

        except Exception as e:
            logger.error("message_handle_error", error=str(e))
            return MessageResponse(
                content="抱歉，处理消息时出现错误，请稍后重试。",
                source=MessageSource.LOCAL,
                latency_ms=int((time.time() - start_time) * 1000),
                conversation_id=conversation_id,
            )

    async def _handle_local(self, request: MessageRequest, decision: RoutingDecision) -> MessageResponse:
        """本地模型处理"""
        use_rag = decision.intent in ["strategy_query", "knowledge_search", "rule_confirm"]
        system_prompt, messages = await self.context_manager.build_messages(
            user_id=request.user_id,
            user_message=request.content,
            use_rag=use_rag,
            is_local=True,
        )

        content = await self.local_model.chat(messages=messages, system=system_prompt)
        return MessageResponse(content=content, source=MessageSource.LOCAL)

    async def _handle_cloud(self, request: MessageRequest, decision: RoutingDecision) -> MessageResponse:
        """云端模型处理"""
        # 脱敏处理
        sanitized_message, mappings = self.sanitizer.sanitize(request.content, decision.privacy_level)

        system_prompt, messages = await self.context_manager.build_messages(
            user_id=request.user_id,
            user_message=sanitized_message,
            use_rag=False,
            is_local=False,
        )

        # 选择供应商和模型
        provider = self.provider_router.choose_provider({"has_image": False})
        model = self.provider_router.choose_model({"has_image": False})

        content = await self.cloud_model.chat(
            messages=messages,
            system=system_prompt,
            provider=provider,
            model=model,
        )

        # 还原脱敏
        content = self.restorer.restore(content, mappings)

        return MessageResponse(content=content, source=MessageSource.CLOUD)

    async def _handle_hybrid(self, request: MessageRequest, decision: RoutingDecision) -> MessageResponse:
        """混合模式: 本地RAG上下文 + 云端推理"""
        # 先检索本地知识
        use_rag = True

        # 脱敏处理
        sanitized_message, mappings = self.sanitizer.sanitize(request.content, decision.privacy_level)

        system_prompt, messages = await self.context_manager.build_messages(
            user_id=request.user_id,
            user_message=sanitized_message,
            use_rag=use_rag,
            is_local=False,  # 用完整system prompt给云端
        )

        # 云端推理
        provider = self.provider_router.choose_provider({"has_image": False})
        model = self.provider_router.choose_model({"has_image": False})
        content = await self.cloud_model.chat(
            messages=messages,
            system=system_prompt,
            provider=provider,
            model=model,
        )

        # 还原脱敏
        content = self.restorer.restore(content, mappings)

        return MessageResponse(content=content, source=MessageSource.CLOUD)
