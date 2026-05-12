"""飞书签名验证"""

import hashlib
import structlog

logger = structlog.get_logger(__name__)


class FeishuAuth:
    """飞书事件签名验证"""

    def __init__(self, verification_token: str = "", encrypt_key: str = ""):
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key

    def verify_signature(self, timestamp: str, nonce: str, body: str, signature: str) -> bool:
        """
        验证飞书事件签名

        Args:
            timestamp: 请求时间戳
            nonce: 随机字符串
            body: 请求体
            signature: 签名

        Returns:
            验证是否通过
        """
        if not self.encrypt_key:
            logger.warning("feishu_encrypt_key_not_set")
            return True  # 未配置加密key时跳过验证

        content = timestamp + nonce + self.encrypt_key + body
        computed = hashlib.sha256(content.encode()).hexdigest()
        return computed == signature

    def handle_challenge(self, event: dict) -> dict | None:
        """
        处理飞书 URL 验证挑战

        首次配置回调URL时，飞书会发送验证请求
        """
        if "challenge" in event:
            return {"challenge": event["challenge"]}
        return None
