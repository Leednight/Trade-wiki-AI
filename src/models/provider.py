"""供应商抽象与降级策略"""

import structlog

logger = structlog.get_logger(__name__)


class ProviderRouter:
    """
    云端供应商选择策略

    决策规则:
    - 含图表/截图需要视觉理解 → siliconflow VL模型
    - 需要深度推理 (R1) → siliconflow DeepSeek-R1
    - 默认 → siliconflow DeepSeek-V3 (性价比最高)
    - 硅基流动不可用 → openai (降级)
    - 都不可用 → 本地模型 (最终降级)
    """

    def choose_provider(self, context: dict) -> str:
        """
        根据上下文选择云端供应商

        Args:
            context: 请求上下文，包含意图、是否含图片等

        Returns:
            供应商名称: "siliconflow" / "openai"
        """
        # 需要视觉理解 → 硅基流动 VL模型 (仍用siliconflow供应商)
        if context.get("has_image"):
            logger.info("provider_choice", reason="visual_understanding", provider="siliconflow")
            return "siliconflow"

        # 默认选择硅基流动
        logger.info("provider_choice", reason="default", provider="siliconflow")
        return "siliconflow"

    def choose_model(self, context: dict) -> str | None:
        """
        根据上下文选择具体模型 (覆盖默认模型)

        Args:
            context: 请求上下文

        Returns:
            模型名 (None表示使用默认模型)
        """
        # 视觉理解
        if context.get("has_image"):
            return None  # chat_with_vision 会自动使用VL模型

        # 深度推理 (如策略回测分析、复杂数学推理)
        if context.get("needs_deep_reasoning"):
            from src.config import get_settings
            settings = get_settings()
            # 可切换到 DeepSeek-R1
            logger.info("model_choice", reason="deep_reasoning", model="deepseek-ai/DeepSeek-R1")
            return "deepseek-ai/DeepSeek-R1"

        return None  # 使用默认模型
