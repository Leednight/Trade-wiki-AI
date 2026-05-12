"""视频转录解析器 - 使用 Whisper 将视频音频转为文本"""

import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)


class VideoParser:
    """视频转录解析器"""

    def __init__(self, model_size: str = "large-v3", device: str = "cuda"):
        self.model_size = model_size
        self.device = device
        self._model = None

    @property
    def model(self):
        """懒加载 Whisper 模型"""
        if self._model is None:
            import whisper
            logger.info("whisper_model_loading", model=self.model_size)
            self._model = whisper.load_model(self.model_size, device=self.device)
            logger.info("whisper_model_loaded")
        return self._model

    async def transcribe(self, file_path: str | Path, language: str = "zh") -> dict:
        """
        转录视频/音频文件

        Args:
            file_path: 视频/音频文件路径
            language: 语言代码 (zh/en)

        Returns:
            {
                "text": "完整转录文本",
                "segments": [{"start": 0.0, "end": 5.0, "text": "..."}, ...],
                "language": "zh"
            }
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")

        logger.info("video_transcribe_start", file=str(path))

        try:
            result = self.model.transcribe(
                str(path),
                language=language,
                verbose=False,
            )

            segments = [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                }
                for seg in result["segments"]
            ]

            output = {
                "text": result["text"].strip(),
                "segments": segments,
                "language": result.get("language", language),
                "source": path.name,
            }

            logger.info(
                "video_transcribe_done",
                file=str(path),
                segments=len(segments),
                duration_seconds=segments[-1]["end"] if segments else 0,
            )
            return output

        except Exception as e:
            logger.error("video_transcribe_error", file=str(path), error=str(e))
            raise
