"""RAG 检索测试 (需要 ChromaDB)"""

import pytest
from src.knowledge.retrieve.rag import RAGRetriever


@pytest.mark.asyncio
async def test_rag_empty_collection():
    """测试空知识库检索"""
    retriever = RAGRetriever()
    results = await retriever.retrieve("什么是均线金叉")
    # 空库应返回空列表
    assert isinstance(results, list)
