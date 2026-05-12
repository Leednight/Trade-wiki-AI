"""云端大模型客户端 - 硅基流动 (主力) / OpenAI (备用)

硅基流动 API 兼容 OpenAI 格式，支持多种开源模型:
- DeepSeek-V3: 通用推理，性价比高
- DeepSeek-R1: 深度推理，带思维链
- Qwen2.5-72B: 中文理解强
- Qwen2.5-VL-7B: 视觉理解 (图表/截图)
"""

import structlog
from openai import AsyncOpenAI

from src.config import get_settings

logger = structlog.get_logger(__name__)

# 硅基流动模型定价 (元/百万token)
# 参考: https://siliconflow.cn/pricing
SILICONFLOW_PRICING = {
    "deepseek-ai/DeepSeek-V3": {"input": 2.0, "output": 8.0},
    "deepseek-ai/DeepSeek-R1": {"input": 4.0, "output": 16.0},
    "Qwen/Qwen2.5-72B-Instruct": {"input": 4.13, "output": 4.13},
    "Qwen/Qwen2.5-7B-Instruct": {"input": 0.55, "output": 0.55},
    "Pro/Qwen/Qwen2.5-VL-7B-Instruct": {"input": 2.0, "output": 2.0},
    # 默认费率 (未知模型)
    "_default": {"input": 2.0, "output": 8.0},
}


class CloudModelClient:
    """云端大模型客户端 - 硅基流动为主力，OpenAI 为备用"""

    def __init__(self):
        settings = get_settings()

        # 主力: 硅基流动
        self.sf_client = AsyncOpenAI(
            api_key=settings.siliconflow.api_key,
            base_url=settings.siliconflow.base_url,
            timeout=settings.siliconflow.timeout,
        )
        self.sf_model = settings.siliconflow.model
        self.sf_vl_model = settings.siliconflow.vl_model

        # 备用: OpenAI (可选)
        self.openai_client = None
        self.openai_model = settings.openai.model
        if settings.openai.api_key:
            self.openai_client = AsyncOpenAI(
                api_key=settings.openai.api_key,
                base_url=settings.openai.base_url,
                timeout=settings.openai.timeout,
            )

        self._cost_tracker = {"total_tokens": 0, "total_cost_cny": 0.0}

    async def chat(
        self,
        messages: list[dict],
        system: str | None = None,
        provider: str = "siliconflow",  # siliconflow / openai
        model: str | None = None,  # 指定模型名，None则用默认
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        调用云端模型对话

        Args:
            messages: 对话消息列表 (应为脱敏后的内容)
            system: 系统提示词
            provider: 云端供应商 (siliconflow / openai)
            model: 指定模型名 (如 "deepseek-ai/DeepSeek-R1")
            temperature: 温度参数
            max_tokens: 最大生成token数

        Returns:
            模型回复文本
        """
        if system:
            messages = [{"role": "system", "content": system}] + messages

        # 确定使用的客户端和模型
        if provider == "siliconflow":
            client = self.sf_client
            use_model = model or self.sf_model
        elif provider == "openai" and self.openai_client:
            client = self.openai_client
            use_model = model or self.openai_model
        else:
            # OpenAI未配置，降级到硅基流动
            logger.warning("cloud_fallback_no_openai", reason="openai_not_configured")
            client = self.sf_client
            use_model = model or self.sf_model
            provider = "siliconflow"

        try:
            response = await client.chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content or ""

            # 记录费用
            usage = response.usage
            if usage:
                self._track_cost(provider, use_model, usage.prompt_tokens, usage.completion_tokens)

            logger.info(
                "cloud_model_chat",
                provider=provider,
                model=use_model,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            )

            return content

        except Exception as e:
            logger.error("cloud_model_error", provider=provider, model=use_model, error=str(e))
            # 降级: 硅基流动 → OpenAI
            if provider == "siliconflow" and self.openai_client:
                logger.warning("cloud_fallback", from_provider="siliconflow", to_provider="openai")
                return await self.chat(
                    messages, system, provider="openai",
                    temperature=temperature, max_tokens=max_tokens,
                )
            raise

    async def chat_with_vision(
        self,
        messages: list[dict],
        image_url: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        调用视觉理解模型 (硅基流动 VL模型)

        Args:
            messages: 对话消息列表
            image_url: 图片URL或base64
            system: 系统提示词
            temperature: 温度参数
            max_tokens: 最大生成token数

        Returns:
            模型回复文本
        """
        if image_url:
            # 在最后一条用户消息中添加图片
            last_msg = messages[-1] if messages else {"role": "user", "content": ""}
            last_msg["content"] = [
                {"type": "text", "text": last_msg.get("content", "")},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
            messages[-1] = last_msg

        return await self.chat(
            messages=messages,
            system=system,
            provider="siliconflow",
            model=self.sf_vl_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _track_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> None:
        """追踪API调用费用"""
        if provider == "siliconflow":
            pricing = SILICONFLOW_PRICING.get(model, SILICONFLOW_PRICING["_default"])
            cost = input_tokens * pricing["input"] / 1_000_000 + output_tokens * pricing["output"] / 1_000_000
        else:
            # OpenAI: ~¥18/M input, ~¥72/M output (按7.2汇率估算)
            cost = input_tokens * 18 / 1_000_000 + output_tokens * 72 / 1_000_000

        self._cost_tracker["total_tokens"] += input_tokens + output_tokens
        self._cost_tracker["total_cost_cny"] += cost

    def get_cost_summary(self) -> dict:
        """获取费用统计"""
        return self._cost_tracker.copy()

    async def health_check(self) -> dict:
        """检查云端API可用性"""
        results = {}

        # 检查硅基流动
        try:
            response = await self.sf_client.chat.completions.create(
                model=self.sf_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            results["siliconflow"] = "available"
        except Exception as e:
            results["siliconflow"] = f"unavailable: {str(e)[:80]}"

        # 检查 OpenAI (如已配置)
        if self.openai_client:
            try:
                response = await self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=5,
                )
                results["openai"] = "available"
            except Exception as e:
                results["openai"] = f"unavailable: {str(e)[:80]}"
        else:
            results["openai"] = "not_configured"

        return results
