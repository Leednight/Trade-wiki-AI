"""通用工具函数"""

from pathlib import Path
from datetime import datetime
from uuid import uuid4


def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    return f"{prefix}_{uuid4().hex[:12]}"


def ensure_dir(path: str | Path) -> Path:
    """确保目录存在"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def now_iso() -> str:
    """当前时间的 ISO 格式字符串"""
    return datetime.now().isoformat()
