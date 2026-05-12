"""飞书消息处理器 - 处理收到的消息和卡片交互"""

import json
import structlog

from src.agent.orchestrator import AgentOrchestrator
from src.config.models import MessageRequest, MessageSource

logger = structlog.get_logger(__name__)

# 卡片交互路由表
CARD_ACTION_HANDLERS = {}


def register_card_action(action: str):
    """注册卡片交互处理器的装饰器"""
    def decorator(func):
        CARD_ACTION_HANDLERS[action] = func
        return func
    return decorator


class FeishuHandler:
    """飞书消息处理器"""

    def __init__(self, bot, orchestrator: AgentOrchestrator | None = None):
        self.bot = bot
        self.orchestrator = orchestrator

    async def handle_message(self, event: dict) -> None:
        """
        处理收到的消息事件

        Args:
            event: 飞书事件数据
        """
        try:
            msg = event.get("message", {})
            sender = event.get("sender", {}).get("sender_id", {})

            msg_type = msg.get("message_type", "text")
            content_str = msg.get("content", "{}")
            open_id = sender.get("open_id", "")

            # 解析消息内容
            content = json.loads(content_str)

            if msg_type == "text":
                text = content.get("text", "")
                await self._handle_text(open_id, text)
            else:
                logger.warning("feishu_unsupported_type", msg_type=msg_type)

        except Exception as e:
            logger.error("feishu_handle_message_error", error=str(e))

    async def handle_card_action(self, event: dict) -> None:
        """处理卡片交互事件"""
        try:
            action_value = event.get("action", {}).get("value", {})
            action_name = action_value.get("action", "")

            handler = CARD_ACTION_HANDLERS.get(action_name)
            if handler:
                await handler(event)
            else:
                logger.warning("feishu_unknown_card_action", action=action_name)

        except Exception as e:
            logger.error("feishu_card_action_error", error=str(e))

    async def _handle_text(self, open_id: str, text: str) -> None:
        """处理文本消息"""
        if not self.orchestrator:
            logger.warning("orchestrator_not_initialized")
            await self.bot.send_text(open_id, "系统初始化中，请稍后...")
            return

        # 构造请求
        request = MessageRequest(
            user_id=open_id,
            content=text,
        )

        # 调用编排器
        response = await self.orchestrator.handle_message(request)

        # 根据回复类型发送
        if response.message_type == "card" and response.card_data:
            await self.bot.send_card(open_id, response.card_data)
        else:
            await self.bot.send_text(open_id, response.content)

        # 深度对话后推送反馈卡片
        if response.source == MessageSource.CLOUD:
            await self._push_feedback_card(open_id, response.conversation_id)

    async def _push_feedback_card(self, open_id: str, conversation_id: str) -> None:
        """推送反馈收集卡片"""
        from src.feishu.card_builder import CardBuilder
        card = CardBuilder.feedback(conversation_id)
        await self.bot.send_card(open_id, card)
