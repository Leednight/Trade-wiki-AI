"""隐私分级检测 - 三重检测机制: 关键词正则 → NER实体识别 → 小模型语义理解"""

import re
import structlog

from src.config.models import PrivacyLevel

logger = structlog.get_logger(__name__)

# P0 关键词库
P0_KEYWORDS = [
    # 持仓相关
    "持仓", "持有", "仓位", "手数", "头寸", "多单", "空单", "做多", "做空",
    "平仓", "建仓", "加仓", "减仓",
    # 账户相关
    "账户", "余额", "资金", "本金", "利润", "亏损", "盈亏", "净值", "回撤", "收益率",
    # 具体参数
    "止损位", "止盈位", "入场价", "出场价", "目标价", "止损价",
    # 具体交易
    "成交价", "挂单", "委托",
]

# P1 关键词库
P1_KEYWORDS = [
    "我的策略", "交易系统", "交易规则", "交易逻辑",
    "我一般", "我通常", "我喜欢", "我偏好", "我的风格", "我的习惯", "我的做法",
    "教你", "记住", "我的思路", "我的方法", "我是这么看的",
]

# 品种+数量/价格的NER模式
POSITION_PATTERNS = [
    # 期货品种
    r"(螺纹钢|铁矿|焦煤|焦炭|沪铜|沪金|沪银|原油|棕榈油|豆粕|菜油|PTA|甲醇|纯碱|玻璃)\s*(\d+)\s*(手|吨)",
    r"(\d+)\s*(手|吨)\s*(螺纹钢|铁矿|焦煤|焦炭|沪铜|沪金|沪银|原油)",
    # 加密货币 (BTC/ETH等)
    r"(BTC|ETH|BNB|SOL|XRP|DOGE|ADA|AVAX)\s*[\s]*(\d+\.?\d*)\s*(个|枚|币|USDT|u)",
    r"(比特币|以太坊|大饼|二饼)\s*[\s]*(\d+\.?\d*)\s*(个|枚|币)",
    r"(买入|做多|做空|卖出)\s*(\d+\.?\d*)\s*(BTC|ETH|BNB|SOL|XRP)",
    # 通用价格模式
    r"(在|于)\s*(\d{3,6}\.?\d*)\s*(入场|买入|做多|做空|卖出)",
    r"止损\s*(\d{3,6}\.?\d*)",
    r"止盈\s*(\d{3,6}\.?\d*)",
]


class PrivacyDetector:
    """隐私分级检测器"""

    def __init__(self, local_model=None):
        """
        Args:
            local_model: 本地小模型客户端 (用于 Layer 3 语义检测，可选)
        """
        self.local_model = local_model
        self._p0_patterns = [re.compile(p) for p in POSITION_PATTERNS]

    def detect(self, message: str) -> PrivacyLevel:
        """
        检测消息的隐私级别

        三重检测:
        1. 关键词正则匹配 (快速)
        2. NER实体识别 (中等)
        3. 小模型语义理解 (较慢，可选)

        Returns:
            隐私级别 P0/P1/P2
        """
        # Layer 1: 关键词匹配
        if self._check_p0_keywords(message):
            logger.info("privacy_detected", level="P0", method="keyword")
            return PrivacyLevel.P0

        # Layer 2: NER模式匹配
        if self._check_position_patterns(message):
            logger.info("privacy_detected", level="P0", method="ner_pattern")
            return PrivacyLevel.P0

        # Layer 1: P1关键词
        if self._check_p1_keywords(message):
            logger.info("privacy_detected", level="P1", method="keyword")
            return PrivacyLevel.P1

        # Layer 3: 小模型语义检测 (异步调用时使用)
        # TODO: 接入本地小模型做语义级隐私检测

        return PrivacyLevel.P2

    def _check_p0_keywords(self, message: str) -> bool:
        """检查P0关键词"""
        return any(kw in message for kw in P0_KEYWORDS)

    def _check_p1_keywords(self, message: str) -> bool:
        """检查P1关键词"""
        return any(kw in message for kw in P1_KEYWORDS)

    def _check_position_patterns(self, message: str) -> bool:
        """检查持仓/价格NER模式"""
        return any(pattern.search(message) for pattern in self._p0_patterns)
