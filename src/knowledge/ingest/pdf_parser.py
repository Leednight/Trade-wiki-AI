"""PDF 解析器 - 使用 Docling 提取文本、表格、公式"""

import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)


class PDFParser:
    """PDF 文档解析器"""

    def __init__(self):
        # Docling 在首次使用时加载模型，这里做懒加载
        self._converter = None

    @property
    def converter(self):
        if self._converter is None:
            from docling.document_converter import DocumentConverter
            self._converter = DocumentConverter()
        return self._converter

    async def parse(self, file_path: str | Path) -> list[dict]:
        """
        解析 PDF 文件，提取结构化文本段落

        Args:
            file_path: PDF 文件路径

        Returns:
            段落列表 [{"content": "...", "page": 1, "type": "text/table"}]
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        logger.info("pdf_parse_start", file=str(path))

        try:
            result = self.converter.convert(str(path))
            # 提取纯文本
            text = result.document.export_to_markdown()

            chunks = []
            for i, paragraph in enumerate(text.split("\n\n")):
                paragraph = paragraph.strip()
                if paragraph:
                    chunks.append({
                        "content": paragraph,
                        "page": i + 1,
                        "type": "text",
                        "source": path.name,
                    })

            logger.info("pdf_parse_done", file=str(path), chunks=len(chunks))
            return chunks

        except Exception as e:
            logger.error("pdf_parse_error", file=str(path), error=str(e))
            raise
