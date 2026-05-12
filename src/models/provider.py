"""供应商抽象与降级策略"""

import structlog

logger = structlog.get_logger(__name__)


class ProviderRouter:
    """
    云端供应商选择策略

    决策规则:
    - 含图表/截图需要视觉理解 → openai (GPT-4o)
    - 默认 → deepseek (性价比最高)
    - deepseek 不可用 → openai (降级)
    - 都不可用 → 本地模型 (最终降级)
    """

    def choose_provider(self, context: dict) -> str:
        """
        根据上下文选择云端供应商

        Args:
            context: 请求上下文，包含意图、是否含图片等

        Returns:
            供应商名称: "deepseek" / "openai"
        """
        # 需要视觉理解
        if context.get("has_image"):
            logger.info("provider_choice", reason="visual_understanding", provider="openai")
            return "openai"

        # 默认选择 DeepSeek
        logger.info("provider_choice", reason="default", provider="deepseek")
        return "deepseek"
