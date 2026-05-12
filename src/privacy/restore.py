"""数据还原 - 将云端回复中的占位符替换回原始值"""

import structlog

logger = structlog.get_logger(__name__)


class DataRestorer:
    """数据还原器 - 将脱敏占位符替换回原始值"""

    def restore(self, cloud_response: str, mappings: dict) -> str:
        """
        还原脱敏数据

        Args:
            cloud_response: 云端回复 (含占位符)
            mappings: 脱敏映射表 {"[COMMODITY_1]": "螺纹钢", ...}

        Returns:
            还原后的回复
        """
        if not mappings:
            return cloud_response

        restored = cloud_response
        for placeholder, original in mappings.items():
            restored = restored.replace(placeholder, original)

        logger.info("data_restored", replacements=len(mappings))
        return restored
