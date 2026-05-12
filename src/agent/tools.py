"""工具注册 - Agent 可调用的工具列表"""

import structlog

from src.knowledge.retrieve.rag import RAGRetriever
from src.knowledge.store.relational import RelationalStore

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """工具注册中心 - 管理Agent可调用的工具"""

    def __init__(self, rag_retriever: RAGRetriever | None = None, db: RelationalStore | None = None):
        self.rag_retriever = rag_retriever or RAGRetriever()
        self.db = db or RelationalStore()
        self._tools = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """注册默认工具"""
        self._tools = {
            "knowledge_search": {
                "name": "knowledge_search",
                "description": "搜索知识库中的相关内容",
                "handler": self._tool_knowledge_search,
            },
            "strategy_query": {
                "name": "strategy_query",
                "description": "查询策略卡片",
                "handler": self._tool_strategy_query,
            },
        }

    def register(self, name: str, description: str, handler) -> None:
        """注册新工具"""
        self._tools[name] = {
            "name": name,
            "description": description,
            "handler": handler,
        }
        logger.info("tool_registered", name=name)

    def get_tool(self, name: str) -> dict | None:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """列出所有工具"""
        return [{"name": t["name"], "description": t["description"]} for t in self._tools.values()]

    async def _tool_knowledge_search(self, query: str, top_k: int = 5) -> str:
        """知识库检索工具"""
        context = await self.rag_retriever.retrieve_with_context(query, top_k)
        return context or "未找到相关知识。"

    async def _tool_strategy_query(self, strategy_name: str = "") -> str:
        """策略查询工具"""
        # TODO: 从 SQLite 查询策略卡片
        return f"策略查询功能待实现 (查询: {strategy_name})"
