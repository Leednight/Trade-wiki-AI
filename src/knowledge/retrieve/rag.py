"""RAG 检索逻辑 - 组合向量检索 + 上下文组装"""

import structlog

from src.knowledge.store.vector import VectorStore, COLLECTION_BOOKS, COLLECTION_VIDEOS, COLLECTION_STRATEGIES
from src.config.models import SearchResult

logger = structlog.get_logger(__name__)


class RAGRetriever:
    """RAG 检索器"""

    def __init__(self, vector_store: VectorStore | None = None):
        self.vector_store = vector_store or VectorStore()

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        collections: list[str] | None = None,
    ) -> list[SearchResult]:
        """
        从多个 Collection 检索相关知识

        Args:
            query: 查询文本
            top_k: 每个Collection返回的结果数
            collections: 要检索的Collection列表，默认全部

        Returns:
            合并后的检索结果，按相似度排序
        """
        if collections is None:
            collections = [COLLECTION_BOOKS, COLLECTION_VIDEOS, COLLECTION_STRATEGIES]

        all_results = []

        for col_name in collections:
            try:
                results = await self.vector_store.search(
                    query=query,
                    collection_name=col_name,
                    top_k=top_k,
                )
                all_results.extend(results)
            except Exception as e:
                logger.warning("rag_collection_search_failed", collection=col_name, error=str(e))

        # 按相似度排序
        all_results.sort(key=lambda r: r.score, reverse=True)

        # 去重并截取 top_k
        seen = set()
        unique_results = []
        for r in all_results:
            key = r.content[:100]  # 用前100字去重
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
            if len(unique_results) >= top_k:
                break

        logger.info("rag_retrieve", query_len=len(query), results=len(unique_results))
        return unique_results

    async def retrieve_with_context(
        self,
        query: str,
        top_k: int = 5,
    ) -> str:
        """
        检索并组装为上下文字符串，可直接注入 Prompt

        Args:
            query: 查询文本
            top_k: 返回结果数

        Returns:
            格式化的上下文字符串
        """
        results = await self.retrieve(query, top_k)

        if not results:
            return ""

        context_parts = ["## 相关知识\n"]
        for i, r in enumerate(results, 1):
            source = f" (来源: {r.source})" if r.source else ""
            context_parts.append(f"[{i}]{source} {r.content}\n")

        return "\n".join(context_parts)
