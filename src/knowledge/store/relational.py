"""SQLite 关系数据库封装 - 存储策略卡片、对话记录、蒸馏样本等"""

import structlog
from pathlib import Path

from sqlalchemy import create_engine, Column, String, Text, Float, Boolean, Integer, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import datetime as sa_datetime

from src.config import get_settings

logger = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    pass


# ============================================================
# ORM 模型定义
# ============================================================

class ConversationORM(Base):
    """对话记录表"""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    message_count = Column(Integer, default=0)
    type = Column(String)  # teaching / review / comparison / feedback / general
    distill_value = Column(String)  # high / medium / low
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=sa_datetime.datetime.now)


class MessageORM(Base):
    """消息记录表"""
    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    conversation_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    model = Column(String)  # qwen2.5-7b / deepseek-v3 / cached
    routing_decision = Column(String)  # local / cloud / hybrid / cache
    privacy_level = Column(String)  # P0 / P1 / P2
    latency_ms = Column(Integer)
    shadow_answer = Column(Text, nullable=True)
    shadow_similarity = Column(Float, nullable=True)
    created_at = Column(DateTime, default=sa_datetime.datetime.now)


class StrategyCardORM(Base):
    """策略卡片表"""
    __tablename__ = "strategies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String)  # entry / exit / risk / general
    description = Column(Text)
    conditions = Column(JSON)  # 策略条件列表
    actions = Column(JSON)  # 操作步骤列表
    risk_management = Column(JSON)  # 风控规则
    reasoning = Column(Text)  # 推理逻辑
    trade_off = Column(Text)  # 权衡取舍
    style_traits = Column(JSON)  # 风格特征
    source_type = Column(String)  # teaching / book / video
    source_conversation_id = Column(String)
    confidence = Column(Float, default=0.0)
    verified = Column(Boolean, default=False)
    tags = Column(JSON)  # 标签列表
    created_at = Column(DateTime, default=sa_datetime.datetime.now)
    updated_at = Column(DateTime, default=sa_datetime.datetime.now, onupdate=sa_datetime.datetime.now)


class FeedbackORM(Base):
    """用户反馈表"""
    __tablename__ = "feedbacks"

    id = Column(String, primary_key=True)
    message_id = Column(String, nullable=False, index=True)
    rating = Column(String, nullable=False)  # thumbs_up / thumbs_down
    correction = Column(Text, nullable=True)
    created_at = Column(DateTime, default=sa_datetime.datetime.now)


class DistillSampleORM(Base):
    """蒸馏训练样本表"""
    __tablename__ = "distill_samples"

    id = Column(String, primary_key=True)
    source_conversation_id = Column(String)
    stage = Column(String, nullable=False)  # sft / cot / dpo
    type = Column(String, nullable=False)  # teaching / review / shadow
    quality_score = Column(Float)
    data = Column(JSON, nullable=False)  # 实际训练数据
    used_in_training = Column(String, nullable=True)  # 训练任务ID
    created_at = Column(DateTime, default=sa_datetime.datetime.now)


class CostRecordORM(Base):
    """API费用记录表"""
    __tablename__ = "cost_records"

    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    provider = Column(String, nullable=False)  # deepseek / openai
    model = Column(String, nullable=False)
    purpose = Column(String)  # routing / deep_inference / data_refine
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_cny = Column(Float, default=0.0)
    created_at = Column(DateTime, default=sa_datetime.datetime.now)


class CacheEntryORM(Base):
    """语义缓存表"""
    __tablename__ = "cache_entries"

    id = Column(String, primary_key=True)
    query_hash = Column(String, nullable=False, unique=True, index=True)
    query_text = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    source = Column(String)  # local / cloud
    hit_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=sa_datetime.datetime.now)
    last_hit_at = Column(DateTime, default=sa_datetime.datetime.now)


# ============================================================
# 数据库管理器
# ============================================================

class RelationalStore:
    """SQLite 关系数据库管理器"""

    def __init__(self):
        settings = get_settings()
        self.db_path = Path(settings.database.sqlite_db_path)
        self._engine = None
        self._session_factory = None

    @property
    def engine(self):
        if self._engine is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._engine = create_engine(
                f"sqlite:///{self.db_path}",
                echo=False,
                connect_args={"check_same_thread": False},
            )
        return self._engine

    @property
    def session_factory(self):
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(self.engine)
        logger.info("database_tables_created", db_path=str(self.db_path))

    def get_session(self):
        """获取数据库会话"""
        return self.session_factory()
