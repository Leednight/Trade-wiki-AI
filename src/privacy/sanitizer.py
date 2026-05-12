"""数据脱敏处理 - 将P1级数据中的敏感实体替换为占位符"""

import re
import structlog
from datetime import datetime

from src.config.models import PrivacyLevel

logger = structlog.get_logger(__name__)

# 脱敏正则模式
SANITIZE_PATTERNS = [
    # 品种名
    (r"(螺纹钢|铁矿|焦煤|焦炭|沪铜|沪金|沪银|原油|棕榈油|豆粕|菜油|PTA|甲醇|纯碱|玻璃)", "COMMODITY"),
    # 数量+单位
    (r"(\d+)\s*(手|吨)", "QUANTITY"),
    # 价格 (4-5位数字)
    (r"(?<!\d)(\d{4,5})(?!\d)", "PRICE"),
    # 止损价格
    (r"止损\s*(\d{3,5})", "STOP_LOSS"),
    # 止盈价格
    (r"止盈\s*(\d{3,5})", "TAKE_PROFIT"),
    # 日期
    (r"(昨天|前天|上周|上周一|上周二|上周三|上周四|上周五|今天|本周)", "DATE"),
]


class DataSanitizer:
    """数据脱敏器"""

    def sanitize(self, message: str, privacy_level: PrivacyLevel) -> tuple[str, dict]:
        """
        对消息进行脱敏处理

        Args:
            message: 原始消息
            privacy_level: 隐私级别

        Returns:
            (脱敏后消息, 映射表)
            映射表格式: {"[COMMODITY_1]": "螺纹钢", ...}
        """
        if privacy_level == PrivacyLevel.P0:
            # P0 不应走到这里，但做保护
            logger.warning("sanitize_p0_message", message="P0 message should not be sent to cloud")
            return message, {}

        if privacy_level == PrivacyLevel.P2:
            # P2 无需脱敏
            return message, {}

        # P1 脱敏处理
        mappings = {}
        sanitized = message
        counter = {}  # 每种类型计数

        for pattern, placeholder_type in SANITIZE_PATTERNS:
            matches = list(re.finditer(pattern, sanitized))
            # 从后往前替换，避免索引偏移
            for match in reversed(matches):
                counter[placeholder_type] = counter.get(placeholder_type, 0) + 1
                tag = f"[{placeholder_type}_{counter[placeholder_type]}]"
                mappings[tag] = match.group(0)
                sanitized = sanitized[:match.start()] + tag + sanitized[match.end():]

        # 记录脱敏信息
        sanitization_id = f"san_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(message) % 10000}"
        logger.info(
            "data_sanitized",
            sanitization_id=sanitization_id,
            privacy_level=privacy_level.value,
            replacements=len(mappings),
        )

        return sanitized, mappings
