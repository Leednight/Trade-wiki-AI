"""意图路由决策 - 判断消息由本地还是云端处理"""

import structlog

from src.config.models import PrivacyLevel, RoutingTarget, RoutingDecision
from src.models.local_client import LocalModelClient
from src.privacy.detector import PrivacyDetector
from src.models.prompts.router import INTENT_CLASSIFICATION_PROMPT, COMPLEXITY_ASSESSMENT_PROMPT

logger = structlog.get_logger(__name__)

# 快速路由规则 (不调用模型，直接匹配)
FAST_ROUTE_RULES = {
    # 意图关键词 → (intent, complexity, target)
    "你好": ("greeting", "low", RoutingTarget.LOCAL),
    "早上好": ("greeting", "low", RoutingTarget.LOCAL),
    "晚上好": ("greeting", "low", RoutingTarget.LOCAL),
    "谢谢": ("greeting", "low", RoutingTarget.LOCAL),
}

# 意图 → 默认路由映射
INTENT_ROUTE_MAP = {
    "greeting": RoutingTarget.LOCAL,
    "strategy_query": RoutingTarget.LOCAL,  # + RAG
    "rule_confirm": RoutingTarget.LOCAL,
    "knowledge_search": RoutingTarget.LOCAL,  # + RAG
    "strategy_analysis": RoutingTarget.CLOUD,
    "teaching": RoutingTarget.HYBRID,
    "trade_review": RoutingTarget.HYBRID,
    "market_data": RoutingTarget.LOCAL,
    "general": RoutingTarget.LOCAL,
}


class AgentRouter:
    """Agent 路由器 - 决定消息由谁处理"""

    def __init__(self, local_model: LocalModelClient | None = None, privacy_detector: PrivacyDetector | None = None):
        self.local_model = local_model
        self.privacy_detector = privacy_detector or PrivacyDetector()

    async def route(self, message: str) -> RoutingDecision:
        """
        路由决策

        Args:
            message: 用户消息

        Returns:
            RoutingDecision
        """
        # Step 1: 快速规则匹配
        for keyword, (intent, complexity, target) in FAST_ROUTE_RULES.items():
            if keyword in message:
                return RoutingDecision(
                    intent=intent,
                    complexity=complexity,
                    privacy_level=PrivacyLevel.P2,
                    target=target,
                    confidence=1.0,
                )

        # Step 2: 隐私检测 (必须，不依赖模型)
        privacy_level = self.privacy_detector.detect(message)

        # Step 3: P0 强制本地
        if privacy_level == PrivacyLevel.P0:
            return RoutingDecision(
                intent="sensitive_query",
                complexity="medium",
                privacy_level=PrivacyLevel.P0,
                target=RoutingTarget.LOCAL,
                confidence=1.0,
            )

        # Step 4: 意图分类 (本地小模型)
        intent = "general"
        complexity = "low"

        if self.local_model:
            try:
                intent = await self.local_model.classify(
                    text=message,
                    labels=["greeting", "strategy_query", "rule_confirm", "knowledge_search",
                            "strategy_analysis", "teaching", "trade_review", "market_data", "general"],
                )
                complexity = await self.local_model.classify(
                    text=message,
                    labels=["low", "medium", "high"],
                )
            except Exception as e:
                logger.warning("route_classification_failed", error=str(e))

        # Step 5: 综合决策
        target = self._decide_target(intent, complexity, privacy_level)

        decision = RoutingDecision(
            intent=intent,
            complexity=complexity,
            privacy_level=privacy_level,
            target=target,
            confidence=0.8 if self.local_model else 0.5,
        )

        logger.info(
            "routing_decision",
            intent=decision.intent,
            complexity=decision.complexity,
            privacy_level=decision.privacy_level.value,
            target=decision.target.value,
        )

        return decision

    def _decide_target(self, intent: str, complexity: str, privacy_level: PrivacyLevel) -> RoutingTarget:
        """综合决策路由目标"""
        # P0 已在前面处理，这里只有 P1/P2

        # P1 + 高复杂度 → HYBRID (本地上下文 + 云端推理)
        if privacy_level == PrivacyLevel.P1 and complexity == "high":
            return RoutingTarget.HYBRID

        # 根据意图映射
        target = INTENT_ROUTE_MAP.get(intent, RoutingTarget.LOCAL)

        # 高复杂度提升到云端
        if complexity == "high" and target == RoutingTarget.LOCAL:
            target = RoutingTarget.CLOUD

        return target
