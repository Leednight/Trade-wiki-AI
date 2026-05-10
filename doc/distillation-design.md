# Trade-Wiki-AI 蒸馏系统设计文档

> 版本: v1.0  
> 日期: 2026-05-10  
> 状态: Draft

---

## 1. 蒸馏目标

### 1.1 核心命题

将用户的交易思维从"外部规则描述"转化为"模型内部权重"，使本地小模型能够：

1. **复现**用户已表达的推理过程
2. **泛化**到用户从未教过的新场景
3. **对齐**用户的风格偏好和风险偏好
4. **减少**对云端大模型的依赖

### 1.2 成长等级与蒸馏阶段对应

```
┌───────────────────────────────────────────────────────────────┐
│                    蒸馏成长等级体系                             │
│                                                                │
│  Level 1: 学徒 (Apprentice)                                    │
│  │  能力: 检索知识库回答已知问题                                │
│  │  实现: RAG + 规则引擎，无需蒸馏                             │
│  │  本地处理: ~50%                                             │
│  │                                                             │
│  Level 2: 助理 (Assistant)  ← Stage 1: 行为克隆               │
│  │  能力: 能像用户一样回答已教过的问题                          │
│  │  实现: SFT监督微调                                          │
│  │  本地处理: ~65%                                             │
│  │                                                             │
│  Level 3: 顾问 (Consultant)  ← Stage 2: 思维蒸馏              │
│  │  能力: 在新场景中复现用户的推理方式                          │
│  │  实现: CoT-SFT (带思维链的监督微调)                        │
│  │  本地处理: ~80%                                             │
│  │                                                             │
│  Level 4: 镜像 (Mirror)  ← Stage 3: 风格对齐                  │
│     能力: 延伸用户直觉，挑战用户决策                            │
│     实现: DPO直接偏好优化                                      │
│     本地处理: ~85%+                                            │
└───────────────────────────────────────────────────────────────┘
```

### 1.3 关键指标

| 指标 | Level 2 目标 | Level 3 目标 | Level 4 目标 |
|------|-------------|-------------|-------------|
| 知识保真度 | > 75% | > 85% | > 90% |
| 推理一致性 | > 50% | > 70% | > 85% |
| 风格匹配度 | > 60% | > 75% | > 90% |
| 本地处理占比 | > 65% | > 80% | > 85% |
| 月度API费用 | < ¥80 | < ¥50 | < ¥30 |

---

## 2. 数据采集

### 2.1 四类蒸馏数据源

#### Type A: 显性教学对话

**定义**：用户主动教授策略、规则、经验的对话

**采集要求**：
- 必须包含完整的问答轮次（至少2轮）
- 记录用户的推理过程（为什么这样做）
- 记录用户的权衡取舍（A vs B，为什么选A）

**示例**：
```json
{
  "type": "teaching",
  "conversation": [
    {"role": "user", "content": "我做突破交易，一般等突破后第一次回踩确认再入场"},
    {"role": "assistant", "content": "为什么不直接追突破？"},
    {"role": "user", "content": "因为假突破太多了，回踩确认胜率更高，虽然利润少一截"}
  ],
  "extracted": {
    "strategy": "突破回踩入场",
    "reasoning": "假突破风险高 → 回踩确认提高胜率 → 愿意牺牲利润换取确定性",
    "trade_off": "利润 vs 胜率，选择胜率"
  }
}
```

#### Type B: 决策复盘对话

**定义**：用户回顾自己的交易决策，分析对错的对话

**采集要求**：
- 必须包含"发生了什么"+"为什么这样做"+"现在怎么看"
- 记录错误模式（最有价值的蒸馏数据！）

**示例**：
```json
{
  "type": "review",
  "conversation": [
    {"role": "user", "content": "昨天螺纹那单，我入场太早了"},
    {"role": "assistant", "content": "当时是什么让你提前入场了？"},
    {"role": "user", "content": "看放量就急了，其实应该等回踩，犯了老毛病"}
  ],
  "extracted": {
    "error_pattern": "放量突破→FOMO→提前入场",
    "correct_behavior": "等待回踩确认",
    "self_awareness": "认识到这是反复出现的错误模式"
  }
}
```

#### Type C: 对比选择对话

**定义**：用户在多个方案中做出选择的对话

**采集要求**：
- 必须包含方案A和方案B
- 必须记录选择理由

**示例**：
```json
{
  "type": "comparison",
  "conversation": [
    {"role": "assistant", "content": "这里有两个入场方案：A直接追入，B等回踩确认。你怎么选？"},
    {"role": "user", "content": "我选B，因为A的止损空间太大，我受不了那种回撤"}
  ],
  "extracted": {
    "choice": "B (保守方案)",
    "reasoning": "止损空间大 → 心理压力大 → 选择更确定的方案",
    "style": "风险厌恶，优先考虑心理舒适度"
  }
}
```

#### Type D: 评价反馈

**定义**：用户对助手回答的正面或负面反馈

**采集要求**：
- 正面反馈：助手说对了 → 正例
- 负面反馈+纠正：助手说错了 → 负例+纠正（价值更高）
- 必须记录纠正内容

**示例**：
```json
{
  "type": "feedback",
  "assistant_answer": "建议立即追入，放量突破通常延续",
  "user_feedback": "thumbs_down",
  "correction": "不对，我的风格是等回踩确认，不是追涨",
  "extracted": {
    "rejected_style": "追涨型",
    "preferred_style": "回踩确认型",
    "dpo_pair": {
      "chosen": "等待回踩确认后再入场",
      "rejected": "立即追入，放量突破通常延续"
    }
  }
}
```

### 2.2 影子蒸馏数据

每条消息发送到云端的同时，本地小模型也并行推理（影子推理），记录两者的差异：

```json
{
  "type": "shadow",
  "query": "当前螺纹钢放量突破3850，怎么操作？",
  "cloud_answer": "虽然出现放量突破，但建议等待回踩确认支撑后再入场...",
  "local_answer": "可以追入，放量突破信号较强...",
  "similarity": 0.45,
  "distill_value": "high",
  "reason": "本地模型缺乏保守风格，需要蒸馏"
}
```

**价值判定规则**：
| 语义相似度 | 蒸馏价值 | 处理方式 |
|-----------|---------|---------|
| > 0.85 | 低 | 小模型已会，跳过 |
| 0.6 - 0.85 | 中 | 保留，作为补充数据 |
| < 0.6 | 高 | ⭐ 优先蒸馏，小模型亟需学习 |

### 2.3 采集存储 Schema

```sql
-- 对话记录表
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    message_count INTEGER DEFAULT 0,
    type TEXT,  -- teaching / review / comparison / feedback / general
    distill_value TEXT,  -- high / medium / low
    processed BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 消息记录表
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,  -- user / assistant
    content TEXT NOT NULL,
    model TEXT,  -- qwen2.5-7b / deepseek-v3 / cached
    routing_decision TEXT,  -- local / cloud / hybrid / cache
    privacy_level TEXT,  -- P0 / P1 / P2
    latency_ms INTEGER,
    shadow_answer TEXT,  -- 本地影子推理结果
    shadow_similarity REAL,  -- 影子推理与实际答案的相似度
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 用户反馈表
CREATE TABLE feedbacks (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id),
    rating TEXT NOT NULL,  -- thumbs_up / thumbs_down
    correction TEXT,  -- 用户纠正内容
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 蒸馏样本表
CREATE TABLE distill_samples (
    id TEXT PRIMARY KEY,
    source_conversation_id TEXT REFERENCES conversations(id),
    stage TEXT NOT NULL,  -- sft / cot / dpo
    type TEXT NOT NULL,  -- teaching / review / comparison / feedback / shadow
    quality_score REAL,  -- 0.0 - 1.0
    data JSON NOT NULL,  -- 实际训练数据
    used_in_training TEXT,  -- 训练任务ID
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. 数据精炼

### 3.1 精炼流水线总览

```
原始对话记录
     │
     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Step 1      │     │  Step 2      │     │  Step 3      │     │  Step 4      │
│  主题切分    │────▶│  思维链提取  │────▶│  风格标注    │────▶│  质量过滤    │
│  (本地小模型) │     │  (云端大模型) │     │  (云端大模型) │     │  (规则+模型) │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                    │
                                                                    ▼
                                                          SFT / DPO 训练集
```

### 3.2 Step 1: 主题切分

**目的**：一次长对话可能涉及多个主题，需要切分为独立的训练样本

**方法**：本地小模型做主题分类 + 规则辅助

```python
TOPIC_SEGMENTATION_PROMPT = """
请将以下对话按主题切分为独立片段。
每个片段应只包含一个主题的讨论。

对话记录：
{conversation}

输出格式（JSON数组）：
[
  {
    "topic": "主题名称",
    "start_index": 消息起始索引,
    "end_index": 消息结束索引,
    "summary": "该片段的简要摘要"
  }
]
"""
```

**切分规则辅助**：
- 时间间隔 > 30分钟的相邻消息 → 强制切分
- 用户发送"换个话题"等指令 → 强制切分
- 上下文窗口保留：切分后每个片段保留前1轮上下文

### 3.3 Step 2: 思维链提取 (CoT Extraction)

**目的**：从对话中提取用户的完整推理过程，这是蒸馏的核心

**方法**：云端大模型做深度推理提取

```python
COT_EXTRACTION_PROMPT = """
你是一个交易思维分析专家。请分析以下交易员与助手的对话，
提取出这个交易员的完整思考过程。

## 对话记录
{conversation_segment}

## 提取要求

1. **情境描述**: 面对的市场情境是什么？
2. **核心决策**: 交易员做出了什么判断/决策？
3. **推理链**: 从观察到判断到决策的完整思考过程，逐步列出
4. **隐性推断**: 有什么假设或直觉没说出口的？请合理推断
5. **权衡取舍**: 决策中放弃了什么，换取了什么？
6. **情绪因素**: 是否有情绪影响决策？如果有，是什么情绪？

## 输出格式 (JSON)
{{
  "situation": "市场情境描述",
  "decision": "核心决策",
  "reasoning_chain": [
    "步骤1: ...",
    "步骤2: ...",
    ...
  ],
  "implicit_assumptions": ["假设1", "假设2"],
  "trade_off": "放弃了X，换取了Y",
  "emotional_factors": ["FOMO", "贪婪", "恐惧", ...],
  "confidence": 0.0-1.0
}}
"""
```

**关键点**：
- 显性推理直接提取（用户说出来的原因）
- 隐性推理由云端大模型推断（用户没说但暗含的逻辑）
- 思维链的粒度要细，每一步都是可独立理解的

### 3.4 Step 3: 风格特征标注

**目的**：为每个样本标注交易风格标签，用于后续风格对齐

```python
STYLE_ANNOTATION_PROMPT = """
基于以下交易员的对话和推理过程，标注其交易风格特征。

## 对话与推理
{conversation_and_reasoning}

## 需要标注的维度

1. **风险偏好**: aggressive / moderate / conservative
2. **决策模式**: intuitive / analytical / hybrid
3. **时间偏好**: scalping / day_trading / swing / position
4. **关注维度**: volume / price / pattern / indicator / fundamentals
5. **入场风格**: breakout / pullback / reversal / momentum
6. **止损风格**: tight / moderate / wide
7. **仓位管理**: all_in / scale_in / fixed_ratio / kelly
8. **优先级**: profit_max / win_rate / risk_control / psychology_comfort

## 输出格式 (JSON)
{{
  "risk_preference": "...",
  "decision_mode": "...",
  "time_preference": "...",
  "focus_dimensions": ["..."],
  "entry_style": "...",
  "stop_loss_style": "...",
  "position_management": "...",
  "priority": "...",
  "style_notes": "额外的风格观察"
}}
"""
```

### 3.5 Step 4: 质量过滤

**目的**：确保只有高质量样本进入训练集

**过滤规则**：

| 规则 | 条件 | 处理 |
|------|------|------|
| 低信息量 | 用户回复仅"嗯""好的""算了" | 丢弃 |
| 无推理 | 有结论但无推理过程 | 保留但标记，后续补充推理 |
| 有推理有结论 | 推理+决策完整 | ⭐ 保留 |
| 有推理有结论有纠偏 | 包含错误反思 | ⭐⭐ 高优先级保留 |
| 情绪化发言 | 明显的情绪化判断，与一贯风格不符 | 丢弃或降权 |
| 矛盾信息 | 与已存策略矛盾 | 保留，标记为"策略更新" |

**质量评分公式**：

```
quality_score = 
    0.3 * has_decision +          # 有明确决策
    0.3 * has_reasoning +         # 有推理过程
    0.2 * has_trade_off +         # 有权衡取舍
    0.1 * has_self_correction +   # 有自我纠偏
    0.1 * style_consistency       # 与已知风格一致
```

### 3.6 输出格式

#### SFT 训练样本 (Stage 1 & 2)

```json
{
  "id": "sft_001",
  "stage": "cot",
  "conversations": [
    {
      "from": "system",
      "value": "你是一个交易助手，内化了用户的交易思维风格。你应该用用户的思维方式来分析和回答交易相关问题。"
    },
    {
      "from": "human",
      "value": "当前市场出现放量突破，是否立即入场？"
    },
    {
      "from": "gpt",
      "value": "<think>\n1. 观察到放量突破信号\n2. 但需要警惕假突破风险\n3. 历史上假突破频繁出现，直接追入胜率不高\n4. 更稳妥的方式是等待回踩确认支撑\n5. 虽然会牺牲部分利润，但胜率显著提升\n6. 这符合'确认优先'的一贯风格\n</think>\n\n不建议立即追入。虽然出现放量突破，但假突破风险较高，历史上直接追入的胜率不理想。建议等待价格回踩突破位确认支撑后再入场，牺牲部分利润换取更高胜率。这更符合我们一贯的'回踩确认'原则。"
    }
  ],
  "style_traits": {
    "risk_preference": "conservative",
    "entry_style": "confirmation_first",
    "priority": "win_rate_over_profit"
  },
  "quality_score": 0.92,
  "source": "teaching_conv_20260510_001"
}
```

#### DPO 训练样本 (Stage 3)

```json
{
  "id": "dpo_001",
  "stage": "dpo",
  "prompt": "当前螺纹钢放量突破3850，怎么操作？",
  "chosen": "虽然出现放量突破，但建议等待回踩确认支撑后再入场。假突破风险较高，回踩确认能显著提高胜率，更符合你的保守风格。",
  "rejected": "放量突破是强信号，建议立即追入，止损设在3820，目标看3900。",
  "style_traits": {
    "chosen_style": "conservative, confirmation_first",
    "rejected_style": "aggressive, chase_breakout"
  },
  "source": "feedback_conv_20260512_003"
}
```

---

## 4. 蒸馏训练

### 4.1 Stage 1: 行为克隆 (SFT)

**目标**：学会像用户一样回答已教过的问题

**训练配置**：

```yaml
# LLaMA-Factory 配置
model_name_or_path: Qwen/Qwen2.5-7B-Instruct
stage: sft
finetuning_type: lora
lora_rank: 16
lora_target: q_proj,v_proj,k_proj,o_proj
lora_alpha: 32
lora_dropout: 0.05

# 量化配置 (QLoRA)
quantization_bit: 4
quantization_type: nf4

# 训练参数
dataset: trading_sft_v1
template: qwen
cutoff_len: 4096
max_samples: 10000
overwrite_output_dir: true

per_device_train_batch_size: 2
gradient_accumulation_steps: 4
learning_rate: 2.0e-4
num_train_epochs: 3
lr_scheduler_type: cosine
warmup_ratio: 0.1
bf16: true

logging_steps: 10
save_steps: 100
eval_steps: 100
per_device_eval_batch_size: 2

output_dir: ./data/lora/sft_v1
```

**数据量要求**：
- 最低启动: 50-100 条
- 基本可用: 200-300 条
- 效果良好: 500+ 条

**训练时间估算** (RTX 4090):
- 100条: ~15分钟
- 300条: ~45分钟
- 500条: ~1.5小时

### 4.2 Stage 2: 思维蒸馏 (CoT-SFT)

**目标**：学会像用户一样思考，不只会结论，还会推理

**关键差异**：训练数据中包含 `<think>...</think>` 思维链

**训练配置**：

```yaml
# 与 Stage 1 相同的基础配置，以下为差异项
dataset: trading_cot_v1
cutoff_len: 8192  # 需要更长上下文容纳思维链

# 思维链特殊处理
train_on_inputs: false  # 不训练输入部分
thinking_tag: "think"   # 思维链标签
```

**思维链模板**：

```
<think>
{step_by_step_reasoning}
</think>

{final_answer}
```

**训练策略**：
- 先用 Stage 1 数据做 warmup (1 epoch)
- 再用 CoT 数据做主训练 (3 epochs)
- 思维链和最终答案都参与loss计算

**数据量要求**：
- 最低启动: 100-200 条 (含思维链)
- 基本可用: 300-500 条
- 效果良好: 800+ 条

### 4.3 Stage 3: 风格对齐 (DPO)

**目标**：在新场景中也能体现用户的交易风格

**训练配置**：

```yaml
model_name_or_path: Qwen/Qwen2.5-7B-Instruct
stage: dpo
finetuning_type: lora
lora_rank: 16
lora_target: q_proj,v_proj,k_proj,o_proj

# DPO专用参数
dataset: trading_dpo_v1
dpo_beta: 0.1           # DPO损失中的KL散度系数
dpo_loss_type: sigmoid   # DPO损失类型
pref_beta: 0.1
pref_loss: sigmoid

per_device_train_batch_size: 2
gradient_accumulation_steps: 4
learning_rate: 5.0e-5    # DPO学习率通常更低
num_train_epochs: 2
bf16: true

output_dir: ./data/lora/dpo_v1
```

**偏好对构建规则**：

| 正例来源 | 负例来源 | 价值 |
|---------|---------|------|
| 用户说"说得对"的回复 | 同一问题的替代回复 | ⭐ |
| 用户的实际决策 | 助手的建议（被用户否决） | ⭐⭐ |
| 影子蒸馏中云端回答 | 影子蒸馏中本地回答（差异大的） | ⭐⭐⭐ |

**数据量要求**：
- 最低启动: 50-100 对
- 基本可用: 200-300 对
- 效果良好: 500+ 对

### 4.4 增量训练策略

每次蒸馏不是从头训练，而是在上一版本基础上增量微调：

```
基座模型 (Qwen2.5-7B)
    │
    ├── + LoRA v1 (SFT, Month 1)     → Level 2
    │       │
    │       ├── + LoRA v2 (CoT-SFT, Month 2)  → Level 3
    │       │       │
    │       │       └── + LoRA v3 (DPO, Month 3) → Level 4
    │       │
    │       └── (或) 合并后重新 LoRA v2' (每季度可选)
    │
    └── 注意: LoRA权重可叠加，也可合并后重新训练
```

**增量 vs 全量训练选择**：

| 条件 | 策略 |
|------|------|
| 每月常规更新 | 增量训练（在上月LoRA基础上继续） |
| 累积3个月+ | 全量训练（合并所有数据重新训练） |
| 升级基座模型 | 全量训练（必须） |
| 效果退化 | 全量训练（回退后重新训练） |

---

## 5. 蒸馏效果评估

### 5.1 评估体系

```
┌─────────────────────────────────────────────────────────────┐
│                   蒸馏效果评估体系                             │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 维度1: 知识保真度 (Knowledge Fidelity)               │    │
│  │                                                      │    │
│  │ 方法: 对比蒸馏模型与用户原始回答的语义相似度          │    │
│  │ 测试集: 50道策略知识题（来自已教策略）                │    │
│  │ 指标: 语义相似度平均值 (cosine similarity)           │    │
│  │ 工具: bge-m3 向量化 + 相似度计算                     │    │
│  │ 合格线: > 0.80                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 维度2: 推理一致性 (Reasoning Consistency)            │    │
│  │                                                      │    │
│  │ 方法: 同一场景问3次，检查推理方向是否一致             │    │
│  │ 测试集: 20个市场场景                                 │    │
│  │ 指标: 推理方向一致率 + CoT路径相似度                 │    │
│  │ 工具: 云端大模型当裁判，对比推理链                   │    │
│  │ 合格线: > 0.70                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 维度3: 风格匹配度 (Style Alignment)                  │    │
│  │                                                      │    │
│  │ 方法A: 自动评估 - 检查回答的风格标签是否匹配          │    │
│  │ 方法B: 盲测 - 用户无法区分哪个是自己的回答           │    │
│  │ 测试集: 10个新场景（未在训练集中出现）               │    │
│  │ 指标: 风格标签匹配率 + 盲测通过率                    │    │
│  │ 合格线: 盲测通过率 > 60%                             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 维度4: 实用性 (Practical Utility)                    │    │
│  │                                                      │    │
│  │ 方法: 对比蒸馏前后的路由分布和用户满意度              │    │
│  │ 指标: 本地处理占比 + 正面反馈率                      │    │
│  │ 合格线: 本地处理 > 80%, 正面反馈率 > 85%            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 评估测试集

```json
{
  "test_set": {
    "knowledge_tests": [
      {
        "id": "kt_001",
        "category": "entry_strategy",
        "question": "突破后应该怎么入场？",
        "expected_answer": "等待回踩确认支撑后再入场",
        "expected_reasoning": ["假突破风险", "回踩确认提高胜率", "牺牲利润换确定性"],
        "expected_style": {"risk_preference": "conservative", "entry_style": "confirmation_first"}
      }
    ],
    "reasoning_tests": [
      {
        "id": "rt_001",
        "category": "new_scenario",
        "scenario": "某品种连续3天放量上涨，今天高开低走收长上影线",
        "expected_direction": "警惕见顶，不追涨，观察后续走势",
        "expected_style_traits": ["conservative", "confirmation_first"]
      }
    ],
    "style_tests": [
      {
        "id": "st_001",
        "scenario": "突破信号出现，但量能一般",
        "option_a": "量能不足，等待确认后再考虑入场",
        "option_b": "突破就是突破，先轻仓试多",
        "expected_choice": "A"
      }
    ]
  }
}
```

### 5.3 评估流程

```
新LoRA权重训练完成
     │
     ▼
加载到Ollama (临时端口)
     │
     ▼
自动跑评估测试集
├── 知识保真度测试 (本地自动)
├── 推理一致性测试 (本地自动)
└── 风格匹配度测试 (本地自动 + 云端裁判)
     │
     ▼
生成评估报告
     │
     ├── 分数提升 → 推送飞书确认 → 用户确认 → 正式部署
     ├── 分数持平 → 保留旧模型，新模型标记为备选
     └── 分数下降 → 丢弃新模型，记录原因
```

---

## 6. 蒸馏飞轮节奏

### 6.1 日常运转

```
每日:
├── 对话记录自动采集 (零干预)
├── 影子蒸馏并行运行 (零干预)
└── 用户偶尔给 👍👎 (5分钟/天)

每周 (数据精炼日, 周日晚):
├── 自动切分本周对话 (5分钟)
├── 批量思维链提取 (云端API, ~¥2)
├── 批量风格标注 (云端API, ~¥1)
├── 质量过滤 (自动)
├── 生成 20-50 条新训练样本
└── 用户抽检确认 (10分钟)

每月 (蒸馏训练日, 月末):
├── 累积 100+ 条新数据
├── 增量LoRA微调 (1-3小时)
├── 自动评估测试集 (30分钟)
├── 生成评估报告
├── 如分数提升 → 部署新模型
└── 更新路由策略 (新模型能处理更多问题)

每季 (大版本升级):
├── 全量数据重新训练
├── 评估是否升级基座模型 (7B → 14B)
├── DPO风格对齐训练
├── 全面评估 + 用户盲测
└── 更新成长等级
```

### 6.2 成长轨迹预期

```
Month 1:
├── 数据: 100-200 条 SFT 样本
├── 训练: Stage 1 SFT
├── 能力: 能回答已教过的基本策略问题
├── 等级: Level 2 (助理)
├── 本地处理: ~65%
└── 月度API费: ~¥80

Month 2:
├── 数据: 300-500 条 CoT 样本
├── 训练: Stage 2 CoT-SFT
├── 能力: 能复现推理过程，在新场景中类比推理
├── 等级: Level 3 (顾问)
├── 本地处理: ~80%
└── 月度API费: ~¥50

Month 3:
├── 数据: 200-500 对偏好对
├── 训练: Stage 3 DPO
├── 能力: 风格对齐，延伸用户直觉
├── 等级: Level 4 (镜像)
├── 本地处理: ~85%
└── 月度API费: ~¥30

Month 6+:
├── 持续增量训练
├── 泛化能力持续提升
├── 本地处理: ~90%+
└── 月度API费: ~¥15
```

---

## 7. 高级蒸馏技巧

### 7.1 影子蒸馏 (Shadow Distillation)

```
┌──────────────────────────────────────────────────────────┐
│                  影子蒸馏流程                              │
│                                                           │
│  用户消息 ──────────┬──────────────────┐                 │
│                     │                   │                 │
│                     ▼                   ▼                 │
│              云端大模型推理      本地小模型推理             │
│              (实际使用)         (影子，不展示给用户)       │
│                     │                   │                 │
│                     ▼                   ▼                 │
│              cloud_answer         shadow_answer           │
│                     │                   │                 │
│                     └───────┬───────────┘                 │
│                             ▼                             │
│                    语义相似度计算                          │
│                             │                             │
│              ┌──────────────┼──────────────┐              │
│              │              │              │              │
│         > 0.85         0.6-0.85        < 0.6            │
│         低价值           中价值          高价值           │
│         跳过             保留           优先蒸馏          │
│                                                           │
│  价值: 自动筛选最有训练价值的样本，减少人工标注负担       │
└──────────────────────────────────────────────────────────┘
```

**自动SFT对构建**：
- 高价值样本：`instruction + cloud_answer` → 直接作为SFT正例
- 同时：`instruction + shadow_answer` → 作为DPO负例

### 7.2 对抗式蒸馏 (Adversarial Distillation)

```
┌──────────────────────────────────────────────────────────┐
│                  对抗式蒸馏流程                            │
│                                                           │
│  定期 (每周1次):                                          │
│                                                           │
│  1. 云端大模型扮演"刁钻的对手"                            │
│     Prompt: "基于这个交易员的已知策略，                   │
│      设计3个最具挑战性的市场场景，                        │
│      让他不得不在矛盾中做出选择"                          │
│                                                           │
│  2. 推送场景给用户                                        │
│     "假设你持有多单，但突然出现利空消息，                  │
│      价格跌到止损位附近但还未触及，你怎么办？"             │
│                                                           │
│  3. 用户的回答 = 最有价值的蒸馏数据                       │
│     因为这种场景触发了深层推理和风格偏好                   │
│                                                           │
│  价值: 最难回答的问题 = 最好的蒸馏数据                    │
│  频率: 不宜过高，每周1-2次，避免用户反感                  │
└──────────────────────────────────────────────────────────┘
```

### 7.3 策略蒸馏 vs 风格蒸馏分离

```
┌───────────────────────────────────────────────────────────┐
│                什么该蒸馏，什么不该蒸馏                      │
│                                                            │
│  ✅ 应该蒸馏到模型权重的 (检索做不到的):                    │
│  ├── 面对不确定性的思考方式                                │
│  ├── 风险偏好和决策权重                                    │
│  ├── 权衡取舍的优先级                                      │
│  ├── 情绪触发的应对模式                                    │
│  └── 直觉性的判断倾向                                      │
│                                                            │
│  ❌ 不需要蒸馏的 (检索就能做的):                            │
│  ├── 具体策略的参数设置                                    │
│  ├── 书籍中的知识点                                        │
│  ├── 历史案例的细节                                        │
│  └── 通用交易知识                                          │
│                                                            │
│  结论:                                                     │
│  • 知识型 → RAG (检索增强)                                │
│  • 推理型 → Distillation (蒸馏)                            │
│  • 两者结合 = 最强助手                                    │
└───────────────────────────────────────────────────────────┘
```

### 7.4 多模型蒸馏 (Model Merging)

```
Phase 3+ 可选策略:

基座模型: Qwen2.5-7B
    │
    ├── LoRA-A: 通用交易知识 (从书籍蒸馏)
    ├── LoRA-B: 用户交易风格 (从对话蒸馏)
    └── LoRA-C: 市场分析能力 (从策略回测蒸馏)

部署时:
├── 方案1: 多LoRA叠加 (Ollama支持)
├── 方案2: Merge LoRA到基座 (Slerp/Dare合并)
└── 方案3: 按场景切换LoRA

优势: 各维度独立训练，互不干扰
```

---

## 8. 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 训练数据不足 | 模型学不到有效模式 | 高 (初期) | 影子蒸馏自动生成；云端大模型辅助扩充；对抗式蒸馏获取高质量数据 |
| 过拟合 | 只会回答训练集中的问题 | 中 | 保留20%数据做验证；Early Stopping；数据增强（同义改写） |
| 灾难性遗忘 | 新训练覆盖旧能力 | 低 | LoRA天然缓解；定期全量训练；版本回滚机制 |
| 风格漂移 | 用户风格自然变化，模型跟不上 | 中 | 持续蒸馏跟上变化；旧数据降权；用户手动校正 |
| 隐私泄露 | 训练数据中的敏感信息被模型记忆 | 低 | 蒸馏前脱敏；训练后做隐私测试；差分隐私 (可选) |
| GPU资源冲突 | 训练时推理不可用 | 中 | 夜间训练；独立GPU (如有双卡)；训练期间降级到云端 |
