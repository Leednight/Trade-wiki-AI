"""Pydantic 数据模型 - 用于 API 请求/响应和内部数据传递"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ============================================================
# 通用枚举
# ============================================================

class PrivacyLevel(str, Enum):
    """隐私分级"""
    P0 = "P0"  # 绝密，仅本地
    P1 = "P1"  # 内部，脱敏后可外传
    P2 = "P2"  # 公开，可直接外传


class RoutingTarget(str, Enum):
    """路由目标"""
    LOCAL = "local"      # 本地小模型
    CLOUD = "cloud"      # 云端大模型
    HYBRID = "hybrid"    # 本地+云端
    CACHE = "cache"      # 语义缓存命中


class MessageSource(str, Enum):
    """消息来源"""
    LOCAL = "local"
    CLOUD = "cloud"
    CACHE = "cache"


class FeedbackRating(str, Enum):
    """用户反馈"""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


class DistillStage(str, Enum):
    """蒸馏阶段"""
    SFT = "sft"
    COT = "cot"
    DPO = "dpo"


class DistillValue(str, Enum):
    """蒸馏数据价值"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============================================================
# 消息相关模型
# ============================================================

class MessageRequest(BaseModel):
    """用户消息请求"""
    user_id: str
    content: str
    message_type: str = "text"  # text / card_action
    context: list[dict] | None = None


class MessageResponse(BaseModel):
    """助手回复"""
    content: str
    message_type: str = "text"  # text / card
    card_data: dict | None = None
    source: MessageSource = MessageSource.LOCAL
    latency_ms: int = 0
    privacy_level: PrivacyLevel = PrivacyLevel.P2
    conversation_id: str = ""


class RoutingDecision(BaseModel):
    """路由决策"""
    intent: str = "general"
    complexity: str = "low"  # low / medium / high
    privacy_level: PrivacyLevel = PrivacyLevel.P2
    target: RoutingTarget = RoutingTarget.LOCAL
    confidence: float = 0.0


# ============================================================
# 知识库相关模型
# ============================================================

class SearchResult(BaseModel):
    """知识库检索结果"""
    content: str
    score: float
    metadata: dict = {}
    source: str = ""  # book / video / strategy / conversation


class DocumentIngestRequest(BaseModel):
    """文档入库请求"""
    file_path: str
    doc_type: str  # pdf / video
    title: str = ""
    author: str = ""


# ============================================================
# 策略卡片模型
# ============================================================

class StrategyCondition(BaseModel):
    """策略条件"""
    metric: str
    operator: str
    value: str


class StrategyAction(BaseModel):
    """策略动作步骤"""
    step: int
    action: str


class RiskManagement(BaseModel):
    """风控规则"""
    stop_loss: str = ""
    position_size: str = ""


class StyleTraits(BaseModel):
    """交易风格特征"""
    risk_preference: str = ""  # aggressive / moderate / conservative
    entry_style: str = ""
    priority: str = ""


class StrategyCard(BaseModel):
    """策略卡片"""
    id: str = ""
    name: str
    category: str = ""  # entry / exit / risk / general
    description: str = ""
    conditions: list[StrategyCondition] = []
    actions: list[StrategyAction] = []
    risk_management: RiskManagement = RiskManagement()
    reasoning: str = ""
    trade_off: str = ""
    style_traits: StyleTraits = StyleTraits()
    source_type: str = "teaching"  # teaching / book / video
    source_conversation_id: str = ""
    confidence: float = 0.0
    verified: bool = False
    tags: list[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============================================================
# 蒸馏相关模型
# ============================================================

class DistillSample(BaseModel):
    """蒸馏训练样本"""
    id: str = ""
    source_conversation_id: str = ""
    stage: DistillStage = DistillStage.SFT
    instruction: str = ""
    thinking_process: list[str] = []
    output: str = ""
    style_traits: dict = {}
    quality_score: float = 0.0


class DistillJob(BaseModel):
    """蒸馏训练任务"""
    job_id: str = ""
    stage: DistillStage = DistillStage.SFT
    dataset_path: str = ""
    base_model: str = ""
    lora_rank: int = 16
    epochs: int = 3
    learning_rate: float = 2e-4
    status: str = "pending"  # pending / running / completed / failed


class DistillResult(BaseModel):
    """蒸馏训练结果"""
    job_id: str
    status: str
    lora_path: str | None = None
    metrics: dict | None = None
    eval_report: dict | None = None
