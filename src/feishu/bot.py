"""飞书 Bot 客户端 - 消息收发"""

import json
import structlog
import lark_oapi as lark
from lark_oapi.api.im.v1 import *

from src.config import get_settings

logger = structlog.get_logger(__name__)


class FeishuBot:
    """飞书 Bot 核心类"""

    def __init__(self):
        settings = get_settings()
        self.app_id = settings.feishu.app_id
        self.app_secret = settings.feishu.app_secret
        self.verification_token = settings.feishu.verification_token
        self.encrypt_key = settings.feishu.encrypt_key
        self._client: lark.Client | None = None

    @property
    def client(self) -> lark.Client:
        if self._client is None:
            self._client = lark.Client.builder() \
                .app_id(self.app_id) \
                .app_secret(self.app_secret) \
                .build()
        return self._client

    async def send_text(self, open_id: str, text: str) -> str:
        """
        发送文本消息

        Args:
            open_id: 用户 open_id
            text: 消息文本

        Returns:
            message_id
        """
        try:
            request = CreateMessageRequest.builder() \
                .receive_id_type("open_id") \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(open_id)
                    .msg_type("text")
                    .content(json.dumps({"text": text}))
                    .build()
                ) \
                .build()

            response = self.client.im.v1.message.create(request)

            if not response.success():
                logger.error("feishu_send_error", code=response.code, msg=response.msg)
                return ""

            logger.info("feishu_text_sent", open_id=open_id, text_len=len(text))
            return response.data.message_id

        except Exception as e:
            logger.error("feishu_send_exception", error=str(e))
            return ""

    async def send_card(self, open_id: str, card: dict) -> str:
        """
        发送交互卡片消息

        Args:
            open_id: 用户 open_id
            card: 卡片 JSON 数据

        Returns:
            message_id
        """
        try:
            request = CreateMessageRequest.builder() \
                .receive_id_type("open_id") \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(open_id)
                    .msg_type("interactive")
                    .content(json.dumps(card))
                    .build()
                ) \
                .build()

            response = self.client.im.v1.message.create(request)

            if not response.success():
                logger.error("feishu_card_send_error", code=response.code, msg=response.msg)
                return ""

            logger.info("feishu_card_sent", open_id=open_id)
            return response.data.message_id

        except Exception as e:
            logger.error("feishu_card_send_exception", error=str(e))
            return ""

    async def update_card(self, message_id: str, card: dict) -> bool:
        """更新已发送的卡片"""
        try:
            request = PatchMessageRequest.builder() \
                .message_id(message_id) \
                .request_body(
                    PatchMessageRequestBody.builder()
                    .content(json.dumps(card))
                    .build()
                ) \
                .build()

            response = self.client.im.v1.message.patch(request)
            return response.success()

        except Exception as e:
            logger.error("feishu_card_update_error", error=str(e))
            return False
