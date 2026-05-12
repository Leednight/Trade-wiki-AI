"""本地 Ollama 模型客户端"""

import structlog
import ollama

from src.config import get_settings

logger = structlog.get_logger(__name__)


class LocalModelClient:
    """Ollama 本地模型客户端 - 处理简单问答、意图分类、隐私检测"""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama.base_url
        self.model = settings.ollama.model
        self.temperature = settings.ollama.temperature
        self.max_tokens = settings.ollama.max_tokens
        self.timeout = settings.ollama.timeout
        self._client: ollama.Client | None = None

    @property
    def client(self) -> ollama.Client:
        """懒加载 Ollama 客户端"""
        if self._client is None:
            self._client = ollama.Client(host=self.base_url)
        return self._client

    async def chat(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        调用本地模型对话

        Args:
            messages: 对话消息列表 [{"role": "user", "content": "..."}]
            system: 系统提示词
            temperature: 温度参数
            max_tokens: 最大生成token数

        Returns:
            模型回复文本
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "options": {
                    "temperature": temperature or self.temperature,
                    "num_predict": max_tokens or self.max_tokens,
                },
            }
            if system:
                kwargs["messages"] = [{"role": "system", "content": system}] + kwargs["messages"]

            response = self.client.chat(**kwargs)
            content = response["message"]["content"]
            logger.info(
                "local_model_chat",
                model=self.model,
                input_tokens=response.get("prompt_eval_count", 0),
                output_tokens=response.get("eval_count", 0),
            )
            return content

        except Exception as e:
            logger.error("local_model_error", error=str(e))
            raise

    async def classify(self, text: str, labels: list[str], system: str | None = None) -> str:
        """
        使用本地模型做分类任务 (意图分类、隐私检测等)

        Args:
            text: 待分类文本
            labels: 候选标签列表
            system: 系统提示词

        Returns:
            分类标签
        """
        labels_str = ", ".join(labels)
        prompt = f"请从以下标签中选择最合适的一个: [{labels_str}]\n\n文本: {text}\n\n只输出标签名称，不要输出其他内容。"
        messages = [{"role": "user", "content": prompt}]

        result = await self.chat(messages, system=system, temperature=0.1, max_tokens=32)
        return result.strip()

    async def health_check(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            self.client.list()
            return True
        except Exception:
            return False
