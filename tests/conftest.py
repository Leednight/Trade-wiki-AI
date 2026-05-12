"""测试公共 fixture"""

import pytest
from src.config import get_settings


@pytest.fixture
def settings():
    """获取测试配置"""
    return get_settings()


@pytest.fixture
def sample_message():
    """示例用户消息"""
    return {
        "user_id": "test_user_001",
        "content": "什么是均线金叉？",
        "message_type": "text",
    }


@pytest.fixture
def sample_p0_message():
    """P0 级敏感消息"""
    return "我持有500手螺纹钢，成本3800，止损3780"


@pytest.fixture
def sample_p1_message():
    """P1 级内部消息"""
    return "我的突破策略一般用1%止损"


@pytest.fixture
def sample_p2_message():
    """P2 级公开消息"""
    return "什么是均线金叉？"
