"""模型调用模块"""

from src.models.local_client import LocalModelClient
from src.models.cloud_client import CloudModelClient

__all__ = ["LocalModelClient", "CloudModelClient"]
