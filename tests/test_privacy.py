"""隐私检测测试"""

from src.privacy.detector import PrivacyDetector
from src.config.models import PrivacyLevel


def test_p0_detection_position():
    """测试 P0 持仓信息检测"""
    detector = PrivacyDetector()

    assert detector.detect("我持有500手螺纹钢") == PrivacyLevel.P0
    assert detector.detect("我的账户余额50万") == PrivacyLevel.P0
    assert detector.detect("止损设在3780") == PrivacyLevel.P0


def test_p1_detection_strategy():
    """测试 P1 策略偏好检测"""
    detector = PrivacyDetector()

    assert detector.detect("我的策略是突破回踩") == PrivacyLevel.P1
    assert detector.detect("我一般在回踩确认后入场") == PrivacyLevel.P1


def test_p2_detection_general():
    """测试 P2 公开信息检测"""
    detector = PrivacyDetector()

    assert detector.detect("什么是均线金叉？") == PrivacyLevel.P2
    assert detector.detect("你好") == PrivacyLevel.P2
