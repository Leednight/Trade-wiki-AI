"""上下文管理 - 对话历史、RAG上下文组装、Prompt构建"""

import structlog

from src.knowledge.retrieve.rag import RAGRetriever
from src.models.prompts.system import SYSTEM_PROMPT, LOCAL_SYSTEM_PROMPT, SYSTEM_PROMPT_WITH_CONTEXT

logger = structlog.get_logger(__name__)

# 对话历史最大轮数
MAX_HISTORY_ROUNDS = 10

# 上下文压缩阈值 (超过此轮数时压缩早期历史)
COMPRESSION_THRESHOLD = 6


class ContextManager:
    """上下文管理器"""

    def __init__(self, rag_retriever: RAGRetriever | None = None):
        self.rag_retriever = rag_retriever or RAGRetriever()
        # 简单的内存对话历史 (生产环境应持久化到SQLite)
        self._history: dict[str, list[dict]] = {}

    def get_history(self, user_id: str) -> list[dict]:
        """获取用户对话历史"""
        return self._history.get(user_id, [])

    def add_message(self, user_id: str, role: str, content: str) -> None:
        """添加消息到历史"""
        if user_id not in self._history:
            self._history[user_id] = []
        self._history[user_id].append({"role": role, "content": content})

        # 超过阈值时压缩早期历史
        if len(self._history[user_id]) > MAX_HISTORY_ROUNDS * 2:
            self._compress_history(user_id)

    def clear_history(self, user_id: str) -> None:
        """清空用户对话历史"""
        self._history.pop(user_id, None)

    async def build_messages(
        self,
        user_id: str,
        user_message: str,
        use_rag: bool = False,
        is_local: bool = True,
    ) -> tuple[str, list[dict]]:
        """
        构建完整的消息列表 (system + history + current)

        Args:
            user_id: 用户ID
            user_message: 当前用户消息
            use_rag: 是否使用RAG检索
            is_local: 是否本地模型 (用简短system prompt)

        Returns:
            (system_prompt, messages)
        """
        # 1. 选择系统 Prompt
        if is_local:
            system_prompt = LOCAL_SYSTEM_PROMPT
        else:
            system_prompt = SYSTEM_PROMPT

        # 2. RAG 检索 (如需要)
        if use_rag:
            rag_context = await self.rag_retriever.retrieve_with_context(user_message, top_k=5)
            if rag_context:
                system_prompt = f"{system_prompt}\n\n{rag_context}"

        # 3. 组装消息列表
        messages = []

        # 添加历史 (最近N轮)
        history = self.get_history(user_id)
        recent_history = history[-MAX_HISTORY_ROUNDS * 2:]  # 每轮2条消息
        messages.extend(recent_history)

        # 添加当前消息
        messages.append({"role": "user", "content": user_message})

        logger.info(
            "context_built",
            user_id=user_id,
            history_rounds=len(recent_history) // 2,
            use_rag=use_rag,
            is_local=is_local,
        )

        return system_prompt, messages

    def _compress_history(self, user_id: str) -> None:
        """
        压缩早期对话历史

        保留最近 COMPRESSION_THRESHOLD 轮完整对话，
        早期对话替换为摘要 (TODO: 用本地小模型生成摘要)
        """
        history = self._history[user_id]
        if len(history) <= COMPRESSION_THRESHOLD * 2:
            return

        # 简单截断：保留最近的对话
        self._history[user_id] = history[-COMPRESSION_THRESHOLD * 2:]
        logger.info("history_compressed", user_id=user_id, kept_rounds=COMPRESSION_THRESHOLD)
