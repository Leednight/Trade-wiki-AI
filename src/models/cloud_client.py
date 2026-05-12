"""云端大模型客户端 - DeepSeek / OpenAI"""

import structlog
from openai import AsyncOpenAI

from src.config import get_settings
from src.config.models import PrivacyLevel

logger = structlog.get_logger(__name__)


class CloudModelClient:
    """云端大模型客户端 - 处理复杂推理、长文总结、多步规划"""

    def __init__(self):
        settings = get_settings()
        # 主力: DeepSeek
        self.deepseek_client = AsyncOpenAI(
            api_key=settings.deepseek.api_key,
            base_url=settings.deepseek.base_url,
            timeout=settings.deepseek.timeout,
        )
        self.deepseek_model = settings.deepseek.model

        # 备用: OpenAI
        self.openai_client = AsyncOpenAI(
            api_key=settings.openai.api_key,
            base_url=settings.openai.base_url,
            timeout=settings.openai.timeout,
        )
        self.openai_model = settings.openai.model

        self._cost_tracker = {"total_tokens": 0, "total_cost_cny": 0.0}

    async def chat(
        self,
        messages: list[dict],
        system: str | None = None,
        provider: str = "deepseek",  # deepseek / openai
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        调用云端模型对话

        Args:
            messages: 对话消息列表 (应为脱敏后的内容)
            system: 系统提示词
            provider: 云端供应商
            temperature: 温度参数
            max_tokens: 最大生成token数

        Returns:
            模型回复文本
        """
        if system:
            messages = [{"role": "system", "content": system}] + messages

        # 选择供应商
        client = self.deepseek_client if provider == "deepseek" else self.openai_client
        model = self.deepseek_model if provider == "deepseek" else self.openai_model

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content or ""

            # 记录费用
            usage = response.usage
            if usage:
                self._track_cost(provider, usage.prompt_tokens, usage.completion_tokens)

            logger.info(
                "cloud_model_chat",
                provider=provider,
                model=model,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            )

            return content

        except Exception as e:
            logger.error("cloud_model_error", provider=provider, error=str(e))
            # 降级: 尝试另一个供应商
            if provider == "deepseek":
                logger.warning("cloud_fallback", from_provider="deepseek", to_provider="openai")
                return await self.chat(messages, system, provider="openai", temperature=temperature, max_tokens=max_tokens)
            raise

    def _track_cost(self, provider: str, input_tokens: int, output_tokens: int) -> None:
        """追踪API调用费用"""
        # DeepSeek: ¥2/M input, ¥8/M output
        # OpenAI: ~¥18/M input, ~¥72/M output (按7.2汇率估算)
        if provider == "deepseek":
            cost = input_tokens * 2 / 1_000_000 + output_tokens * 8 / 1_000_000
        else:
            cost = input_tokens * 18 / 1_000_000 + output_tokens * 72 / 1_000_000

        self._cost_tracker["total_tokens"] += input_tokens + output_tokens
        self._cost_tracker["total_cost_cny"] += cost

    def get_cost_summary(self) -> dict:
        """获取费用统计"""
        return self._cost_tracker.copy()

    async def health_check(self) -> dict:
        """检查云端API可用性"""
        results = {}
        for provider, client, model in [
            ("deepseek", self.deepseek_client, self.deepseek_model),
            ("openai", self.openai_client, self.openai_model),
        ]:
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=5,
                )
                results[provider] = "available"
            except Exception as e:
                results[provider] = f"unavailable: {str(e)[:50]}"
        return results
