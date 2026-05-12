"""语义缓存 - 相似问题命中缓存则不调模型"""

import structlog

from src.knowledge.store.vector import VectorStore

logger = structlog.get_logger(__name__)

# 缓存命中相似度阈值
CACHE_SIMILARITY_THRESHOLD = 0.92


class SemanticCache:
    """语义缓存 - 基于向量相似度的问答缓存"""

    def __init__(self, vector_store: VectorStore | None = None):
        self.vector_store = vector_store or VectorStore()

    async def get(self, query: str) -> str | None:
        """
        查询缓存

        Args:
            query: 用户问题

        Returns:
            缓存的答案，未命中返回 None
        """
        results = await self.vector_store.search(
            query=query,
            collection_name="cache_entries",
            top_k=1,
        )

        if results and results[0].score >= CACHE_SIMILARITY_THRESHOLD:
            logger.info("cache_hit", query_len=len(query), score=results[0].score)
            return results[0].content

        logger.info("cache_miss", query_len=len(query))
        return None

    async def set(self, query: str, answer: str, source: str = "local") -> None:
        """
        写入缓存

        Args:
            query: 问题
            answer: 答案
            source: 来源 (local/cloud)
        """
        # 用答案的hash作为ID
        import hashlib
        doc_id = hashlib.md5(f"{query}:{answer}".encode()).hexdigest()[:16]

        await self.vector_store.ingest(
            collection_name="cache_entries",
            documents=[answer],
            ids=[doc_id],
            metadatas=[{"query": query[:200], "source": source}],
        )

        logger.info("cache_set", query_len=len(query), answer_len=len(answer))
