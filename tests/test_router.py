"""路由决策测试"""

from src.agent.router import AgentRouter
from src.config.models import PrivacyLevel, RoutingTarget


def test_fast_route_greeting():
    """测试快速路由 - 问候"""
    router = AgentRouter(local_model=None)  # 不依赖模型
    decision = await router.route("你好")

    assert decision.intent == "greeting"
    assert decision.target == RoutingTarget.LOCAL
    assert decision.confidence == 1.0


def test_p0_forced_local():
    """测试 P0 强制本地"""
    router = AgentRouter(local_model=None)
    decision = await router.route("我持有500手螺纹钢")

    assert decision.privacy_level == PrivacyLevel.P0
    assert decision.target == RoutingTarget.LOCAL


# 注意: 异步测试需要 pytest-asyncio
import pytest


@pytest.mark.asyncio
async def test_route_without_model():
    """测试无模型时的路由降级"""
    router = AgentRouter(local_model=None)
    decision = await router.route("什么是均线金叉？")

    # 无模型时默认走本地
    assert decision.target == RoutingTarget.LOCAL
