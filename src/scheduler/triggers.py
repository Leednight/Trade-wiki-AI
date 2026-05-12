"""事件触发器 (Phase 2 完善)"""

import structlog

logger = structlog.get_logger(__name__)


class EventTriggers:
    """事件触发器"""

    # TODO: Phase 2 实现
    # - 行情突破关键位 → 推送预警
    # - 新教学完成 → 推送策略确认卡片
    # - 蒸馏训练完成 → 推送评估报告
    # - API费用超预算 → 推送告警

    @staticmethod
    async def check_price_alerts():
        """检查行情预警"""
        logger.info("trigger_check_price_alerts")

    @staticmethod
    async def on_teaching_complete(strategy_id: str):
        """教学完成事件"""
        logger.info("trigger_teaching_complete", strategy_id=strategy_id)

    @staticmethod
    async def on_distill_complete(job_id: str):
        """蒸馏完成事件"""
        logger.info("trigger_distill_complete", job_id=job_id)
