"""ChromaDB 向量数据库封装（内嵌模式，无需Docker）"""

import structlog
import chromadb
from pathlib import Path

from src.config import get_settings
from src.config.models import SearchResult

logger = structlog.get_logger(__name__)

# Collection 名称常量
COLLECTION_BOOKS = "book_chunks"
COLLECTION_VIDEOS = "video_chunks"
COLLECTION_STRATEGIES = "strategy_cards"
COLLECTION_CONVERSATIONS = "conversation_pairs"


class VectorStore:
    """ChromaDB 向量存储（内嵌模式）"""

    def __init__(self):
        settings = get_settings()
        self.persist_path = Path(settings.database.chromadb_path)
        self._client: chromadb.ClientAPI | None = None

    @property
    def client(self) -> chromadb.ClientAPI:
        """懒加载 ChromaDB 客户端（内嵌模式）"""
        if self._client is None:
            self.persist_path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.persist_path))
            logger.info("chromadb_initialized", path=str(self.persist_path))
        return self._client

    def _get_or_create_collection(self, name: str) -> chromadb.Collection:
        """获取或创建 Collection"""
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    async def ingest(
        self,
        collection_name: str,
        documents: list[str],
        ids: list[str],
        metadatas: list[dict] | None = None,
    ) -> int:
        """
        文档入库

        Args:
            collection_name: Collection 名称
            documents: 文档内容列表
            ids: 文档ID列表
            metadatas: 元数据列表

        Returns:
            入库数量
        """
        collection = self._get_or_create_collection(collection_name)

        # ChromaDB 默认使用内置的 all-MiniLM-L6-v2 做向量化
        # TODO: 后续替换为 bge-m3 本地向量化
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas or [{}] * len(documents),
        )

        logger.info("vector_ingest", collection=collection_name, count=len(documents))
        return len(documents)

    async def search(
        self,
        query: str,
        collection_name: str = COLLECTION_BOOKS,
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[SearchResult]:
        """
        向量检索

        Args:
            query: 查询文本
            collection_name: Collection 名称
            top_k: 返回前K个结果
            where: 元数据过滤条件

        Returns:
            检索结果列表
        """
        try:
            collection = self._get_or_create_collection(collection_name)
            kwargs = {
                "query_texts": [query],
                "n_results=min(top_k, collection.count())" if collection.count() > 0 else "n_results=0",
            }
            if where:
                kwargs["where"] = where

            if collection.count() == 0:
                return []

            kwargs["n_results"] = min(top_k, collection.count())
            results = collection.query(**kwargs)

            search_results = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    search_results.append(SearchResult(
                        content=doc,
                        score=1.0 - results["distances"][0][i] if results["distances"] else 0.0,
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                        source=results["metadatas"][0][i].get("source", "") if results["metadatas"] else "",
                    ))

            logger.info(
                "vector_search",
                collection=collection_name,
                query_len=len(query),
                results=len(search_results),
            )
            return search_results

        except Exception as e:
            logger.error("vector_search_error", error=str(e))
            return []

    async def delete_document(self, collection_name: str, doc_id: str) -> bool:
        """删除指定文档"""
        try:
            collection = self._get_or_create_collection(collection_name)
            collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            logger.error("vector_delete_error", error=str(e))
            return False

    async def get_collection_stats(self) -> dict:
        """获取所有 Collection 的统计信息"""
        collections = self.client.list_collections()
        stats = {}
        for col in collections:
            stats[col.name] = {
                "count": col.count(),
            }
        return stats
