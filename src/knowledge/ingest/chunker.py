"""文本分块器 - 将长文本分割为适合向量化的段落"""

import structlog

logger = structlog.get_logger(__name__)


class TextChunker:
    """文本分块器"""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50, separator: str = "\n\n"):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def chunk(self, text: str, metadata: dict | None = None) -> list[dict]:
        """
        将文本分割为固定大小的块

        Args:
            text: 原始文本
            metadata: 附加到每个块的元数据

        Returns:
            [{"content": "...", "index": 0, "metadata": {...}}, ...]
        """
        if not text.strip():
            return []

        # 先按自然段落分割
        paragraphs = text.split(self.separator)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # 合并过短的段落，分割过长的段落
        chunks = []
        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            # 如果当前块+新段落不超过限制，合并
            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}".strip() if current_chunk else para
            else:
                # 保存当前块
                if current_chunk:
                    chunks.append(self._make_chunk(current_chunk, chunk_index, metadata))
                    chunk_index += 1
                    # 保留 overlap
                    current_chunk = self._get_overlap(current_chunk) + para
                else:
                    # 单个段落就超长，强制分割
                    sub_chunks = self._split_long_text(para, metadata, chunk_index)
                    chunks.extend(sub_chunks)
                    chunk_index += len(sub_chunks)
                    if sub_chunks:
                        current_chunk = self._get_overlap(sub_chunks[-1]["content"])

        # 最后一块
        if current_chunk.strip():
            chunks.append(self._make_chunk(current_chunk, chunk_index, metadata))

        logger.info("text_chunked", total_chunks=len(chunks), original_length=len(text))
        return chunks

    def _make_chunk(self, content: str, index: int, metadata: dict | None = None) -> dict:
        return {
            "content": content.strip(),
            "index": index,
            "metadata": metadata or {},
        }

    def _get_overlap(self, text: str) -> str:
        """获取文本末尾的 overlap 部分"""
        if len(text) <= self.chunk_overlap:
            return text
        return text[-self.chunk_overlap:]

    def _split_long_text(self, text: str, metadata: dict | None = None, start_index: int = 0) -> list[dict]:
        """强制分割超长文本"""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk_text = text[i : i + self.chunk_size]
            if chunk_text.strip():
                chunks.append(self._make_chunk(chunk_text, start_index + len(chunks), metadata))
        return chunks
