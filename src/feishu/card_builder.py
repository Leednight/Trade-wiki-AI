"""飞书交互卡片构建器"""

import structlog

logger = structlog.get_logger(__name__)


class CardBuilder:
    """飞书卡片消息构建器"""

    @staticmethod
    def strategy_confirm(strategy: dict) -> dict:
        """构建策略确认卡片"""
        conditions_text = "\n".join(
            f"{i+1}. {c}" for i, c in enumerate(strategy.get("conditions", []))
        ) or "暂无"

        risk_text = ""
        rm = strategy.get("risk_management", {})
        if rm.get("stop_loss"):
            risk_text += f"- 止损: {rm['stop_loss']}\n"
        if rm.get("position_size"):
            risk_text += f"- 仓位: {rm['position_size']}\n"

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {"tag": "plain_text", "content": "📋 新策略卡片待确认"},
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**策略名称**: {strategy.get('name', '')}\n**类型**: {strategy.get('category', '')}\n**描述**: {strategy.get('description', '')}",
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**核心条件**:\n{conditions_text}\n\n**风控规则**:\n{risk_text}\n**推理逻辑**: {strategy.get('reasoning', '')}",
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "✅ 确认保存"},
                            "type": "primary",
                            "value": {"action": "confirm_strategy", "strategy_id": strategy.get("id", "")},
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "✏️ 修改"},
                            "type": "default",
                            "value": {"action": "edit_strategy", "strategy_id": strategy.get("id", "")},
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "❌ 放弃"},
                            "type": "danger",
                            "value": {"action": "discard_strategy", "strategy_id": strategy.get("id", "")},
                        },
                    ],
                },
            ],
        }

    @staticmethod
    def alert(symbol: str, price: float, level: float, strategy_name: str = "") -> dict:
        """构建行情预警卡片"""
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "red",
                "title": {"tag": "plain_text", "content": "⚠️ 行情预警"},
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**品种**: {symbol}\n**当前价**: {price}\n**关注位**: {level}\n\n距离关注位仅差 **{abs(price - level):.0f}** 点！\n\n基于你的「{strategy_name}」策略，建议密切关注。",
                    },
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "📊 查看分析"},
                            "type": "primary",
                            "value": {"action": "view_analysis", "symbol": symbol},
                        },
                    ],
                },
            ],
        }

    @staticmethod
    def feedback(conversation_id: str) -> dict:
        """构建反馈收集卡片"""
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "turquoise",
                "title": {"tag": "plain_text", "content": "💬 这个回答对你有帮助吗？"},
            },
            "elements": [
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "👍 有帮助"},
                            "type": "primary",
                            "value": {"action": "feedback_positive", "conversation_id": conversation_id},
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "👎 不太对"},
                            "type": "default",
                            "value": {"action": "feedback_negative", "conversation_id": conversation_id},
                        },
                    ],
                },
            ],
        }

    @staticmethod
    def weekly_report(report: dict) -> dict:
        """构建周报卡片"""
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "purple",
                "title": {"tag": "plain_text", "content": "📋 本周交易总结"},
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": report.get("summary", "暂无数据"),
                    },
                },
            ],
        }
