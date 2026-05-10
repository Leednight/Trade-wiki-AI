# Trade-Wiki-AI 系统架构文档

> 版本: v1.0  
> 日期: 2026-05-10  
> 状态: Draft

---

## 1. 架构总览

### 1.1 设计原则

| 原则 | 说明 |
|------|------|
| **本地优先** | 数据和推理尽可能在本地完成，云端作为增强而非依赖 |
| **渐进蒸馏** | 小模型通过持续蒸馏逐步替代大模型，降低API依赖 |
| **隐私护城河** | 敏感数据分级，P0级永不外传，P1级脱敏后外传 |
| **模块解耦** | 各模块通过接口通信，可独立升级和替换 |
| **离线可用** | 断网场景下核心功能（本地问答、知识检索）仍可用 |

### 1.2 系统架构图

```
                         ┌─────────────────┐
                         │    飞书 IM       │
                         │  (用户交互入口)   │
                         └────────┬────────┘
                                  │ HTTPS
                                  ▼
                    ┌──────────────────────────┐
                    │     内网穿透 (frp/ngrok)   │
                    │     (开发阶段使用)         │
                    └────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      ▼                      │
          │           ┌─────────────────────┐           │
          │           │   API Gateway       │           │
          │           │   (FastAPI)         │           │
          │           └─────────┬───────────┘           │
          │                     │                       │
          │     ┌───────────────┼───────────────┐       │
          │     │               │               │       │
          │     ▼               ▼               ▼       │
          │ ┌─────────┐ ┌───────────┐ ┌────────────┐  │
          │ │ Feishu  │ │ Scheduler │ │ Admin API  │  │
          │ │ Handler │ │  Service  │ │ (管理接口) │  │
          │ └────┬────┘ └─────┬─────┘ └────────────┘  │
          │      │            │                        │
   ───────┼──────┼────────────┼────────────────────────┼──────
          │      ▼            ▼                        │
          │ ┌─────────────────────────────────────┐   │
          │ │         Agent Orchestrator           │   │
          │ │         (LlamaIndex)                 │   │
          │ │                                      │   │
          │ │  ┌──────────┐  ┌──────────────┐     │   │
          │ │  │  Router   │  │  Context Mgr │     │   │
          │ │  │ (路由决策) │  │ (上下文管理) │     │   │
          │ │  └──────────┘  └──────────────┘     │   │
          │ │                                      │   │
          │ │  ┌──────────┐  ┌──────────────┐     │   │
          │ │  │ Privacy  │  │   Semantic   │     │   │
          │ │  │  Guard   │  │    Cache     │     │   │
          │ │  │ (隐私守卫)│  │  (语义缓存)  │     │   │
          │ │  └──────────┘  └──────────────┘     │   │
          │ └──────────────┬──────────────────────┘   │
          │                │                           │
          │     ┌──────────┼──────────┐               │
          │     │                     │               │
          │     ▼                     ▼               │
          │ ┌─────────────┐  ┌───────────────┐       │
          │ │ Local Model │  │ Cloud Model   │       │
          │ │  (Ollama)   │  │   Client      │       │
          │ │             │  │               │       │
          │ │ Qwen2.5-7B │  │ DeepSeek-V3   │       │
          │ │ + LoRA      │  │ / GPT-4o      │       │
          │ └──────┬──────┘  └───────┬───────┘       │
          │        │                 │               │
          │        ▼                 │               │
   本地环境 │ ┌──────────────────┐   │               │
          │ │  Knowledge Store  │   │               │
          │ │                    │   │               │
          │ │ ┌──────────────┐  │   │               │
          │ │ │  ChromaDB    │  │   │               │
          │ │ │ (向量索引)    │  │   │               │
          │ │ └──────────────┘  │   │               │
          │ │ ┌──────────────┐  │   │               │
          │ │ │   SQLite     │  │   │               │
          │ │ │ (结构化数据)  │  │   │               │
          │ │ └──────────────┘  │   │               │
          │ │ ┌──────────────┐  │   │               │
          │ │ │   Neo4j      │  │   │               │
          │ │ │ (知识图谱P2) │  │   │               │
          │ │ └──────────────┘  │   │               │
          │ └──────────────────┘   │               │
          │                         │               │
   ───────┼─────────────────────────┼───────────────┼──────
          │                         ▼               │
          │               ┌─────────────────┐      │
          │               │  Cloud LLM API  │      │
          │               │                 │      │
          │               │ DeepSeek-V3     │      │
          │               │ GPT-4o          │      │
          │               └─────────────────┘      │
          └────────────────────────────────────────┘
```

---

## 2. 模块详细设计

### 2.1 API Gateway (FastAPI)

**职责**：统一的HTTP入口，路由到各服务模块

```
FastAPI
├── /api/feishu/event         # 飞书事件回调
├── /api/feishu/command       # 飞书命令回调
├── /api/chat/message         # 通用聊天接口
├── /api/knowledge/upload     # 知识库文件上传
├── /api/knowledge/search     # 知识库检索
├── /api/strategy/            # 策略卡片CRUD
├── /api/distill/status       # 蒸馏训练状态
├── /api/distill/trigger      # 触发蒸馏训练
├── /api/admin/config         # 系统配置
└── /api/health               # 健康检查
```

**关键中间件**：
- 请求鉴权（飞书签名验证 / API Key）
- 请求日志（记录所有交互，供蒸馏使用）
- 错误处理（统一错误格式）
- 限流（防止API滥用）

### 2.2 Agent Orchestrator (LlamaIndex)

**职责**：核心智能编排层，协调路由、检索、模型调用

```
Agent Orchestrator
│
├── Router (路由决策)
│   ├── 输入: 用户消息 + 对话上下文
│   ├── 处理:
│   │   1. 本地小模型做意图分类
│   │   2. Privacy Guard 做隐私检测
│   │   3. 规则引擎做快速匹配
│   │   4. 综合决策: local / cloud / hybrid
│   └── 输出: 路由决策 + 置信度
│
├── Context Manager (上下文管理)
│   ├── 对话历史管理（滑动窗口 / 摘要压缩）
│   ├── RAG 上下文组装（检索结果 + 策略卡片 + 规则）
│   ├── Prompt 模板管理
│   └── 上下文压缩（送云端前压缩历史，节省token）
│
├── Privacy Guard (隐私守卫)
│   ├── P0 检测: 持仓/账户/资金 关键词 + 模型检测
│   ├── P1 检测: 策略参数/具体标的/价格
│   ├── P2 检测: 通用知识/公开信息
│   ├── 脱敏管道: P1数据替换为占位符
│   └── 还原管道: 云端回复中还原占位符
│
├── Semantic Cache (语义缓存)
│   ├── 向量化用户问题
│   ├── 与缓存库做相似度检索 (阈值: 0.92)
│   ├── 命中 → 直接返回缓存答案
│   └── 未命中 → 正常处理流程
│
└── Tool Registry (工具注册)
    ├── knowledge_search: 知识库检索
    ├── strategy_query: 策略卡片查询
    ├── market_data: 行情数据获取
    ├── trade_log: 交易日志记录
    └── teaching: 教学模式触发
```

**路由决策矩阵**：

| 意图 | 隐私级别 | 复杂度 | 路由目标 | 预期延迟 |
|------|---------|--------|---------|---------|
| 问候/闲聊 | P2 | 低 | 本地 | <1s |
| 策略查询 | P2 | 低 | 本地+RAG | <1.5s |
| 规则确认 | P1 | 低 | 本地 | <1s |
| 持仓分析 | P0 | 中 | 本地+RAG | <2s |
| 教学对话 | P1 | 高 | 云端+本地上下文 | 2-5s |
| 策略推理 | P1 | 高 | 云端+RAG | 2-5s |
| 长文总结 | P2 | 高 | 云端 | 2-5s |
| 情绪提醒 | P0 | 中 | 本地 | <1s |

### 2.3 Local Model (Ollama)

**职责**：本地推理引擎，处理80%日常问题

```
Ollama
├── 基座模型: Qwen2.5-7B-Instruct (Q4_K_M量化)
│   ├── 显存占用: ~6GB
│   ├── 推理速度: ~30 tokens/s (RTX 3090)
│   └── 上下文长度: 32K
│
├── LoRA 权重: 按版本管理
│   ├── v1_base: 原始模型 (无LoRA)
│   ├── v2_sft: Stage 1 SFT微调后
│   ├── v3_cot: Stage 2 CoT蒸馏后
│   └── v4_dpo: Stage 3 DPO对齐后
│
├── 模型切换: API热加载LoRA权重
│   └── POST /api/gguf/load_lora
│
└── 多模型支持 (预留)
    ├── Qwen2.5-14B (显存足够时升级)
    └── DeepSeek-Coder-7B (回测代码生成)
```

**本地模型调用链**：

```python
# 伪代码
async def local_inference(messages, tools=None):
    # 1. 组装Prompt (System + Context + User)
    system_prompt = build_system_prompt(
        rules=load_active_rules(),       # 当前生效的规则卡片
        strategies=load_strategies(),     # 策略摘要
        style_profile=load_style()        # 风格画像
    )
    
    # 2. RAG检索 (如需要)
    if needs_rag(messages):
        contexts = chromadb_search(messages[-1]["content"], top_k=5)
        messages = inject_context(messages, contexts)
    
    # 3. 调用Ollama
    response = ollama.chat(
        model="qwen2.5-7b-instruct",
        messages=messages,
        system=system_prompt,
        options={"temperature": 0.7, "num_predict": 1024}
    )
    
    return response
```

### 2.4 Cloud Model Client

**职责**：云端大模型调用客户端，含脱敏/还原管道

```
Cloud Model Client
│
├── Provider Abstraction (多供应商抽象)
│   ├── DeepSeekClient
│   │   ├── model: "deepseek-chat" (DeepSeek-V3)
│   │   ├── pricing: ¥2/M input, ¥8/M output
│   │   └── features: 64K context, CoT
│   │
│   ├── OpenAIClient
│   │   ├── model: "gpt-4o"
│   │   ├── pricing: $2.5/M input, $10/M output
│   │   └── features: 128K context, Vision
│   │
│   └── (可扩展其他供应商)
│
├── 请求管道
│   ├── 输入 → Privacy Guard脱敏 → Prompt组装 → API调用
│   └── 响应 → 本地还原 → 返回
│
├── 上下文压缩
│   ├── 本地小模型压缩历史对话 (10轮 → 500字摘要)
│   └── 仅发送压缩后的上下文 + 当前问题
│
├── 重试与降级
│   ├── 超时重试 (3次, 指数退避)
│   ├── 供应商降级 (DeepSeek → OpenAI → 本地)
│   └── 限流处理 (429 → 排队等待)
│
└── 成本追踪
    ├── 每次调用记录token消耗和费用
    ├── 日/周/月费用统计
    └── 超预算告警
```

### 2.5 Knowledge Store

**职责**：多模态知识存储与检索

```
Knowledge Store
│
├── ChromaDB (向量索引)
│   ├── Collections:
│   │   ├── book_chunks       # 书籍段落
│   │   ├── video_chunks      # 视频转录段落
│   │   ├── strategy_cards    # 策略卡片向量
│   │   └── conversation_pairs # 历史问答对
│   │
│   ├── Embedding: text-embedding-3-small / bge-m3
│   ├── Chunk策略: 512 tokens, overlap 50
│   └── 检索: cosine similarity, top_k=5
│
├── SQLite (结构化数据)
│   ├── Tables:
│   │   ├── strategies        # 策略卡片
│   │   ├── conversations     # 对话记录
│   │   ├── trade_logs        # 交易日志
│   │   ├── teaching_records  # 教学记录
│   │   ├── distill_samples   # 蒸馏训练样本
│   │   ├── feedback_records  # 用户反馈
│   │   ├── cache_entries     # 语义缓存
│   │   └── cost_records      # API费用记录
│   │
│   └── 索引: 全文搜索 + 常用查询索引
│
├── Neo4j (知识图谱 - Phase 2)
│   ├── Nodes:
│   │   ├── Strategy          # 策略
│   │   ├── Condition         # 条件
│   │   ├── Risk              # 风险
│   │   ├── Case              # 案例
│   │   ├── Concept           # 概念
│   │   └── Book              # 来源书籍
│   │
│   └── Relationships:
│       ├── REQUIRES          # 策略需要条件
│       ├── HAS_RISK          # 策略存在风险
│       ├── HAS_CASE          # 策略有案例
│       ├── RELATED_TO        # 概念关联
│       ├── DERIVED_FROM      # 策略源自书籍
│       └── CONFLICTS_WITH    # 策略冲突
│
└── 文件存储
    ├── /data/raw/books/       # 原始书籍文件
    ├── /data/raw/videos/      # 原始视频文件
    ├── /data/raw/transcripts/ # 转录文本
    ├── /data/refined/         # 精炼后数据
    └── /data/models/lora/     # LoRA权重文件
```

### 2.6 Distill Service

**职责**：蒸馏训练全流程管理

```
Distill Service
│
├── DataCollector (数据采集)
│   ├── 对话记录自动写入
│   ├── 反馈标注收集
│   └── 影子蒸馏并行推理
│
├── DataRefiner (数据精炼)
│   ├── 主题切分 (本地小模型)
│   ├── 思维链提取 (云端大模型)
│   ├── 风格特征标注 (云端大模型)
│   ├── 质量过滤 (规则 + 模型)
│   └── 输出: SFT/DPO训练集JSON
│
├── Trainer (训练执行)
│   ├── LLaMA-Factory集成
│   ├── QLoRA配置管理
│   ├── 训练任务调度
│   ├── Checkpoint管理
│   └── 训练指标监控
│
├── Evaluator (效果评估)
│   ├── 知识保真度测试
│   ├── 推理一致性测试
│   ├── 风格匹配度测试
│   └── 自动评估报告
│
└── ModelDeployer (模型部署)
    ├── LoRA权重版本管理
    ├── Ollama模型热加载
    ├── A/B测试 (新旧模型对比)
    └── 回滚机制
```

### 2.7 Scheduler Service

**职责**：定时任务和事件触发

```
Scheduler Service (APScheduler)
│
├── Cron Jobs (定时任务)
│   ├── 08:00  盘前策略预计算
│   ├── 08:30  盘前策略推送
│   ├── 15:30  盘后交易日志分析
│   ├── 20:00  每日数据精炼
│   ├── Sun 20:00  周报生成
│   └── 1st/Month  月度蒸馏评估
│
├── Event Triggers (事件触发)
│   ├── 行情突破关键位 → 推送预警
│   ├── 新教学完成 → 推送策略确认卡片
│   ├── 蒸馏训练完成 → 推送评估报告
│   └── API费用超预算 → 推送告警
│
└── Task Queue (任务队列)
    ├── 优先级: critical > high > normal > low
    ├── 并发控制: 本地训练任务独占GPU
    └── 失败重试: 3次, 指数退避
```

---

## 3. 技术选型

### 3.1 核心技术栈

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|---------|
| **Web框架** | FastAPI | 0.110+ | 异步高性能，自动OpenAPI文档 |
| **Agent框架** | LlamaIndex | 0.10+ | 知识库场景最佳，RAG原生支持 |
| **本地模型运行时** | Ollama | latest | 一键部署，OpenAI兼容API |
| **向量数据库** | ChromaDB | 0.4+ | 轻量本地，Python原生，零配置 |
| **关系数据库** | SQLite | 3.x | 轻量本地，无需部署 |
| **图数据库** | Neo4j Community | 5.x | 策略关系推理 (Phase 2) |
| **训练框架** | LLaMA-Factory | latest | LoRA/DPO一站式，支持Qwen系列 |
| **视频转录** | Whisper large-v3 | latest | 本地运行，中文效果好 |
| **PDF解析** | Docling | latest | 表格/公式保留好 |
| **任务调度** | APScheduler | 3.10+ | 轻量，Python原生 |
| **IM集成** | 飞书开放平台SDK | latest | 官方Python SDK |
| **内网穿透** | frp / Cloudflare Tunnel | latest | 开发阶段暴露本地服务 |
| **编程语言** | Python | 3.10+ | ML生态最完善 |
| **包管理** | uv | latest | 高速，替代pip |

### 3.2 模型选型

| 用途 | 模型 | 部署方式 | 参数量 | 量化 |
|------|------|---------|--------|------|
| 本地路由+简单问答 | Qwen2.5-7B-Instruct | Ollama本地 | 7B | Q4_K_M |
| 云端深度推理 | DeepSeek-V3 | API调用 | 671B (MoE) | N/A |
| 云端视觉理解 | GPT-4o | API调用 | N/A | N/A |
| 视频转录 | Whisper large-v3 | 本地 | 1.5B | FP16 |
| 文本向量化 | bge-m3 | 本地 | 568M | FP16 |
| 蒸馏基座 | Qwen2.5-7B-Instruct | LLaMA-Factory | 7B | QLoRA 4bit |

### 3.3 硬件需求

| 配置项 | 最低要求 | 推荐配置 |
|--------|---------|---------|
| GPU | RTX 3060 (12GB) | RTX 4090 (24GB) |
| RAM | 16GB | 32GB |
| 存储 | 100GB SSD | 500GB NVMe SSD |
| CPU | 8核 | 16核 |

**GPU显存分配**：

```
RTX 4090 (24GB) 典型分配:
├── Qwen2.5-7B Q4推理: ~6GB
├── bge-m3向量化: ~1.5GB
├── 余量: ~16.5GB
└── QLoRA训练时: 推理暂停, 训练占用 ~18GB
```

---

## 4. 数据流设计

### 4.1 用户消息处理流

```
飞书消息 → API Gateway → Feishu Handler
    │
    ▼
Agent Orchestrator
    │
    ├── 1. Semantic Cache 检查
    │   └── 命中 → 直接返回缓存答案 (跳过后续步骤)
    │
    ├── 2. Router 意图分类 (本地小模型)
    │   └── 输出: intent + complexity + routing_target
    │
    ├── 3. Privacy Guard 隐私检测
    │   └── 输出: privacy_level + 脱敏消息 (如需)
    │
    ├── 4. 根据路由决策分发
    │   │
    │   ├── [LOCAL] ──────────────────────────┐
    │   │   ├── RAG检索 (如需)               │
    │   │   ├── 组装Prompt                   │
    │   │   ├── 调用Ollama                   │
    │   │   └── 返回回复                     │
    │   │                                    │
    │   ├── [CLOUD] ─────────────────────────┐│
    │   │   ├── 脱敏处理 (如需)             ││
    │   │   ├── 上下文压缩                   ││
    │   │   ├── 调用云端API                  ││
    │   │   ├── 本地还原脱敏                 ││
    │   │   └── 返回回复                     ││
    │   │                                    ││
    │   └── [HYBRID] ───────────────────────┐││
    │       ├── RAG检索本地知识             │││
    │       ├── 脱敏+压缩                   │││
    │       ├── 调用云端 (带本地上下文)      │││
    │       ├── 本地还原+后处理             │││
    │       └── 返回回复                     │││
    │                                         │││
    ├── 5. 影子蒸馏 (异步)                   │││
    │   └── 本地同时跑一遍, 与最终答案对比   │││
    │                                         │││
    ├── 6. 记录对话 (自动)                   │││
    │   └── 写入SQLite + 蒸馏数据队列        │││
    │                                         │││
    └── 7. 更新语义缓存                      │││
                                            │││
    ◀────────────────────────────────────────┘││
                                             ││
    回复 ──→ 飞书消息发送 ────────────────────┘│
                                              │
    对话记录 ──→ Distill DataCollector ◀───────┘
```

### 4.2 知识入库流

```
用户上传文件 (PDF/视频)
    │
    ▼
API Gateway → Knowledge Handler
    │
    ├── [PDF文件]
    │   ├── Docling 解析 → 提取文本+表格+公式
    │   ├── 文本分块 (512 tokens, overlap 50)
    │   ├── bge-m3 向量化
    │   ├── 存入 ChromaDB (book_chunks collection)
    │   └── 元数据存入 SQLite
    │
    └── [视频文件]
        ├── Whisper large-v3 转录
        ├── 生成时间戳段落
        ├── 文本分块 + 向量化
        ├── 存入 ChromaDB (video_chunks collection)
        └── 元数据存入 SQLite
```

### 4.3 教学处理流

```
用户教学对话
    │
    ▼
Agent Orchestrator → 识别教学模式
    │
    ├── 1. 苏格拉底提问 (主动追问细节)
    │
    ├── 2. 策略提取 (云端大模型)
    │   └── 输出: 结构化策略卡片 JSON
    │
    ├── 3. 飞书推送确认卡片
    │   ┌───────────────────────────────────┐
    │   │ 📋 新策略卡片待确认               │
    │   │                                    │
    │   │ 名称: 突破回踩入场                │
    │   │ 条件: 1)放量突破 2)回踩确认支撑    │
    │   │ 止损: 突破位下方1%                │
    │   │ 仓位: 计划仓位的1/3               │
    │   │                                    │
    │   │ [✅ 确认] [✏️ 修改] [❌ 放弃]      │
    │   └───────────────────────────────────┘
    │
    ├── 4. 用户确认 → 写入策略库 + 向量化
    │
    └── 5. 异步: 关联知识库已有策略 (Phase 2)
```

---

## 5. 部署架构

### 5.1 开发阶段

```
本地台式机 (Windows/Linux + RTX 4090)
├── Docker Compose
│   ├── app (FastAPI主服务)
│   ├── ollama (本地模型)
│   ├── chromadb (向量数据库)
│   ├── neo4j (Phase 2)
│   └── scheduler (定时任务)
│
├── frp / Cloudflare Tunnel → 飞书回调
│
└── 本地文件系统
    ├── /data/ (知识库数据)
    └── /models/ (模型权重)
```

### 5.2 生产阶段 (可选)

```
云服务器 (轻量)
├── Nginx 反向代理
├── frp server (内网穿透中转)
└── 飞书回调入口

本地台式机
├── frp client → 连接云服务器
└── 所有核心服务仍运行在本地
```

> **核心原则**：即使部署云服务器，也仅作为网络中转，所有计算和数据仍在本地。

---

## 6. 目录结构

```
Trade-wiki-AI/
├── doc/                         # 文档
│   ├── PRD.md
│   ├── architecture.md
│   ├── distillation-design.md
│   ├── feishu-integration.md
│   ├── data-privacy.md
│   └── roadmap.md
│
├── src/                         # 源代码
│   ├── main.py                  # FastAPI入口
│   ├── config/                  # 配置管理
│   │   ├── settings.py
│   │   └── models.py
│   │
│   ├── gateway/                 # API Gateway
│   │   ├── router.py
│   │   └── middleware.py
│   │
│   ├── feishu/                  # 飞书集成
│   │   ├── bot.py
│   │   ├── handler.py
│   │   ├── card_builder.py
│   │   └── auth.py
│   │
│   ├── agent/                   # Agent编排
│   │   ├── orchestrator.py
│   │   ├── router.py            # 意图路由
│   │   ├── context.py           # 上下文管理
│   │   ├── cache.py             # 语义缓存
│   │   └── tools.py             # 工具注册
│   │
│   ├── models/                  # 模型调用
│   │   ├── local_client.py      # Ollama客户端
│   │   ├── cloud_client.py      # 云端API客户端
│   │   ├── provider.py          # 供应商抽象
│   │   └── prompts/             # Prompt模板
│   │       ├── system.py
│   │       ├── router.py
│   │       ├── teaching.py
│   │       └── distill.py
│   │
│   ├── knowledge/               # 知识库
│   │   ├── ingest/              # 数据摄入
│   │   │   ├── pdf_parser.py
│   │   │   ├── video_parser.py
│   │   │   └── chunker.py
│   │   ├── store/               # 存储层
│   │   │   ├── vector.py        # ChromaDB
│   │   │   ├── relational.py    # SQLite
│   │   │   └── graph.py         # Neo4j (P2)
│   │   └── retrieve/            # 检索层
│   │       ├── rag.py
│   │       └── hybrid.py
│   │
│   ├── privacy/                 # 隐私保护
│   │   ├── detector.py
│   │   ├── sanitizer.py
│   │   └── restore.py
│   │
│   ├── teaching/                # 教学系统
│   │   ├── strategy_card.py
│   │   ├── socratic.py
│   │   └── extractor.py
│   │
│   ├── distill/                 # 蒸馏系统
│   │   ├── collector.py
│   │   ├── refiner.py
│   │   ├── trainer.py
│   │   ├── evaluator.py
│   │   └── deployer.py
│   │
│   ├── scheduler/               # 定时任务
│   │   ├── jobs.py
│   │   └── triggers.py
│   │
│   └── common/                  # 公共组件
│       ├── logger.py
│       ├── crypto.py
│       └── utils.py
│
├── data/                        # 数据目录 (gitignore)
│   ├── raw/
│   ├── refined/
│   ├── eval/
│   └── lora/
│
├── tests/                       # 测试
│   ├── test_router.py
│   ├── test_privacy.py
│   ├── test_rag.py
│   └── test_distill.py
│
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

---

## 7. 关键接口定义

### 7.1 消息处理接口

```python
# src/agent/orchestrator.py

class MessageRequest(BaseModel):
    """用户消息请求"""
    user_id: str
    content: str
    message_type: str = "text"  # text / card_action
    context: list[dict] | None = None  # 对话历史

class MessageResponse(BaseModel):
    """助手回复"""
    content: str
    message_type: str = "text"  # text / card
    card_data: dict | None = None  # 飞书卡片数据
    source: str  # local / cloud / cache
    latency_ms: int
    privacy_level: str  # P0 / P1 / P2
    conversation_id: str

class AgentOrchestrator:
    async def handle_message(self, request: MessageRequest) -> MessageResponse:
        """处理用户消息的主入口"""
        ...
```

### 7.2 知识库接口

```python
# src/knowledge/store/vector.py

class KnowledgeStore:
    async def ingest_document(self, doc_id: str, chunks: list[str], metadata: dict) -> int:
        """入库文档段落，返回入库数量"""
        ...
    
    async def search(self, query: str, top_k: int = 5, filter: dict | None = None) -> list[SearchResult]:
        """向量检索"""
        ...
    
    async def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        ...

class SearchResult(BaseModel):
    content: str
    score: float
    metadata: dict
    source: str  # book / video / strategy / conversation
```

### 7.3 蒸馏接口

```python
# src/distill/trainer.py

class DistillJob(BaseModel):
    """蒸馏训练任务"""
    job_id: str
    stage: str  # sft / cot / dpo
    dataset_path: str
    base_model: str
    lora_rank: int = 16
    epochs: int = 3
    learning_rate: float = 2e-4

class DistillResult(BaseModel):
    """蒸馏训练结果"""
    job_id: str
    status: str  # running / completed / failed
    lora_path: str | None = None
    metrics: dict | None = None  # loss, eval_score etc.
    eval_report: dict | None = None

class DistillService:
    async def start_training(self, job: DistillJob) -> str:
        """启动蒸馏训练，返回job_id"""
        ...
    
    async def get_status(self, job_id: str) -> DistillResult:
        """查询训练状态"""
        ...
    
    async def deploy_model(self, job_id: str) -> bool:
        """部署训练好的LoRA权重到Ollama"""
        ...
```

---

## 8. 监控与运维

### 8.1 监控指标

| 指标 | 采集方式 | 告警条件 |
|------|---------|---------|
| API响应延迟 | FastAPI middleware | P99 > 10s |
| 本地模型推理速度 | Ollama metrics | < 10 tokens/s |
| 云端API调用次数 | Cloud Client | 日调用 > 100次 |
| 云端API费用 | Cloud Client | 日费用 > ¥5 |
| 语义缓存命中率 | Cache metrics | < 30% |
| 路由准确率 | 人工抽检 | < 80% |
| GPU显存占用 | nvidia-smi | > 90% |
| 磁盘空间 | system metrics | > 80% |

### 8.2 日志规范

```python
# 统一日志格式
{
    "timestamp": "2026-05-10T09:30:00Z",
    "level": "INFO",
    "module": "agent.router",
    "trace_id": "trace_xxx",
    "user_id": "user_xxx",
    "message": "Route decision: intent=strategy_query, target=local, confidence=0.92",
    "extra": {
        "intent": "strategy_query",
        "privacy_level": "P2",
        "routing_target": "local",
        "latency_ms": 245
    }
}
```
