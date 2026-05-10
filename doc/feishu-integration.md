# Trade-Wiki-AI 飞书集成设计文档

> 版本: v1.0  
> 日期: 2026-05-10  
> 状态: Draft

---

## 1. 概述

### 1.1 设计目标

飞书是用户与交易助手交互的主要入口，设计需满足：

- **即时响应**：简单问题1.5s内回复，复杂问题5s内回复
- **丰富交互**：支持文本、富文本、交互卡片等多种消息类型
- **主动触达**：助手可主动推送预警、报告、教学确认等
- **无缝对接**：消息收发与内部Agent编排层解耦

### 1.2 飞书Bot能力范围

| 能力 | 说明 | 支持状态 |
|------|------|---------|
| 接收文本消息 | 用户在飞书中发送文本给Bot | ✅ Phase 1 |
| 发送文本消息 | Bot回复文本消息 | ✅ Phase 1 |
| 发送富文本消息 | 带格式的消息（加粗、链接等） | ✅ Phase 1 |
| 发送交互卡片 | 带按钮的卡片，用户可点击操作 | ✅ Phase 1 |
| 接收卡片交互 | 处理用户点击卡片按钮 | ✅ Phase 1 |
| 群聊支持 | 在群聊中@Bot触发 | P1 Phase 2 |
| 消息更新 | 更新已发送的卡片内容 | P1 Phase 2 |
| 文件上传 | 用户发送PDF/视频文件给Bot | P1 Phase 2 |
| 定时消息 | 定时推送盘前分析等 | P1 Phase 2 |

---

## 2. 飞书Bot配置

### 2.1 应用创建

```
飞书开放平台 → 创建企业自建应用
├── 应用名称: 交易助手
├── 应用描述: 你的AI交易知识助手
├── 图标: 📈 定制图标
└── 可用范围: 仅自己
```

### 2.2 权限配置

| 权限 | 权限ID | 用途 | 必要性 |
|------|--------|------|--------|
| 获取与发送单聊消息 | im:message | 收发私聊消息 | 必须 |
| 读取用户信息 | contact:user.base | 识别用户身份 | 必须 |
| 发送卡片消息 | im:message:send_as_bot | 发送交互卡片 | 必须 |
| 获取群组信息 | im:chat | 群聊支持 (Phase 2) | 可选 |
| 上传文件 | im:resource | 接收文件 (Phase 2) | 可选 |

### 2.3 事件订阅

| 事件 | Event Key | 用途 |
|------|-----------|------|
| 接收消息 | im.message.receive_v1 | 处理用户发送的消息 |
| 卡片交互 | card.action.trigger | 处理用户点击卡片按钮 |

### 2.4 回调地址

```
开发环境:
  https://{frp-domain}/api/feishu/event

生产环境:
  https://{domain}/api/feishu/event
```

---

## 3. 消息处理流程

### 3.1 接收消息流程

```
飞书服务器
    │
    │ POST /api/feishu/event
    │ (带签名验证)
    ▼
API Gateway
    │
    ├── 1. 验证签名 (X-Lark-Signature)
    │   └── 不通过 → 返回 403
    │
    ├── 2. 解析事件类型
    │   ├── url_verification → 返回 challenge (首次验证)
    │   ├── im.message.receive_v1 → 消息处理
    │   └── card.action.trigger → 卡片交互处理
    │
    ├── 3. 消息处理
    │   ├── 提取消息内容 (文本/卡片)
    │   ├── 提取用户ID
    │   ├── 去重 (同一消息可能推送多次)
    │   └── 转发到 FeishuHandler
    │
    └── 4. 立即返回 200 OK (飞书要求3s内响应)
         └── 异步处理消息，发送回复
```

### 3.2 发送消息流程

```
Agent Orchestrator 生成回复
    │
    ▼
FeishuHandler
    │
    ├── 1. 确定消息类型
    │   ├── 简短文本 → text 消息
    │   ├── 带格式的内容 → post (富文本) 消息
    │   └── 策略卡片/确认/报告 → interactive (卡片) 消息
    │
    ├── 2. 构建消息体
    │   ├── text: {"text": "..."}
    │   ├── post: {"zh_cn": {"title": "...", "content": [...]}}
    │   └── interactive: 卡片JSON (见卡片设计)
    │
    ├── 3. 调用飞书API发送
    │   └── POST https://open.feishu.cn/open-apis/im/v1/messages
    │       ?receive_id_type=open_id
    │       Body: {receive_id, msg_type, content}
    │
    └── 4. 记录发送日志
```

---

## 4. 卡片设计

### 4.1 策略确认卡片

用于教学后确认新策略：

```json
{
  "config": {
    "wide_screen_mode": true
  },
  "header": {
    "template": "blue",
    "title": {
      "tag": "plain_text",
      "content": "📋 新策略卡片待确认"
    }
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**策略名称**: 突破回踩入场\n**类型**: 入场策略\n**适用场景**: 趋势行情中的突破点"
      }
    },
    {
      "tag": "hr"
    },
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**核心条件**:\n1. 放量突破关键位\n2. 等待回踩确认支撑\n3. 支撑有效后入场\n\n**风控规则**:\n- 止损: 突破位下方1%\n- 仓位: 计划仓位的1/3\n\n**推理逻辑**: 假突破频繁，回踩确认提高胜率，牺牲利润换确定性"
      }
    },
    {
      "tag": "hr"
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "✅ 确认保存"
          },
          "type": "primary",
          "value": {
            "action": "confirm_strategy",
            "strategy_id": "strat_001"
          }
        },
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "✏️ 修改"
          },
          "type": "default",
          "value": {
            "action": "edit_strategy",
            "strategy_id": "strat_001"
          }
        },
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "❌ 放弃"
          },
          "type": "danger",
          "value": {
            "action": "discard_strategy",
            "strategy_id": "strat_001"
          }
        }
      ]
    }
  ]
}
```

### 4.2 策略回测结果卡片

```json
{
  "config": {
    "wide_screen_mode": true
  },
  "header": {
    "template": "green",
    "title": {
      "tag": "plain_text",
      "content": "📊 策略回测结果"
    }
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**策略**: 突破回踩入场\n**回测周期**: 2024-01-01 ~ 2026-04-30\n**品种**: 螺纹钢主力"
      }
    },
    {
      "tag": "hr"
    },
    {
      "tag": "column_set",
      "flex_mode": "bisect",
      "background_style": "default",
      "columns": [
        {
          "tag": "column",
          "width": "weighted",
          "weight": 1,
          "elements": [
            {
              "tag": "div",
              "text": {
                "tag": "lark_md",
                "content": "**胜率**\n62.3%"
              }
            }
          ]
        },
        {
          "tag": "column",
          "width": "weighted",
          "weight": 1,
          "elements": [
            {
              "tag": "div",
              "text": {
                "tag": "lark_md",
                "content": "**盈亏比**\n1.8:1"
              }
            }
          ]
        }
      ]
    },
    {
      "tag": "column_set",
      "flex_mode": "bisect",
      "background_style": "default",
      "columns": [
        {
          "tag": "column",
          "width": "weighted",
          "weight": 1,
          "elements": [
            {
              "tag": "div",
              "text": {
                "tag": "lark_md",
                "content": "**最大回撤**\n8.3%"
              }
            }
          ]
        },
        {
          "tag": "column",
          "width": "weighted",
          "weight": 1,
          "elements": [
            {
              "tag": "div",
              "text": {
                "tag": "lark_md",
                "content": "**夏普比率**\n1.45"
              }
            }
          ]
        }
      ]
    },
    {
      "tag": "hr"
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "📈 查看详情"
          },
          "type": "primary",
          "value": {
            "action": "view_backtest_detail",
            "backtest_id": "bt_001"
          }
        },
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "⚙️ 调整参数"
          },
          "type": "default",
          "value": {
            "action": "adjust_params",
            "backtest_id": "bt_001"
          }
        }
      ]
    }
  ]
}
```

### 4.3 行情预警卡片

```json
{
  "config": {
    "wide_screen_mode": true
  },
  "header": {
    "template": "red",
    "title": {
      "tag": "plain_text",
      "content": "⚠️ 行情预警"
    }
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**品种**: 螺纹钢 RB2610\n**当前价**: 3843\n**关注位**: 3850 (突破位)\n\n距离突破位仅 **7点**！\n\n基于你的「突破回踩入场」策略，建议密切关注。"
      }
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "📊 查看分析"
          },
          "type": "primary",
          "value": {
            "action": "view_analysis",
            "symbol": "RB2610"
          }
        },
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "🔕 暂停该品种预警"
          },
          "type": "default",
          "value": {
            "action": "mute_alert",
            "symbol": "RB2610"
          }
        }
      ]
    }
  ]
}
```

### 4.4 周报/月报卡片

```json
{
  "config": {
    "wide_screen_mode": true
  },
  "header": {
    "template": "purple",
    "title": {
      "tag": "plain_text",
      "content": "📋 本周交易总结"
    }
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**2026年第19周 (5.5 - 5.9)**"
      }
    },
    {
      "tag": "hr"
    },
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**📊 交易概况**\n- 交易次数: 5次\n- 盈利: 3次 | 亏损: 2次\n- 胜率: 60%\n- 周盈亏: +2.3%\n\n**🎯 策略一致性**\n- 遵守策略: 4次 ✅\n- 偏离策略: 1次 ⚠️ (周二螺纹钢追涨)\n\n**💡 助手观察**\n- 你的「突破回踩」策略本周胜率75%，表现稳定\n- 周二追涨偏离策略，与#7错误模式(FOMO追涨)一致\n- 建议加强放量突破时的情绪管理\n\n**📈 蒸馏进展**\n- 本周新增教学数据: 12条\n- 当前模型版本: v3 (Level 3)\n- 本地处理占比: 82%"
      }
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "📊 详细分析"
          },
          "type": "primary",
          "value": {
            "action": "view_weekly_detail",
            "week": "2026-W19"
          }
        }
      ]
    }
  ]
}
```

### 4.5 反馈收集卡片

每段深度对话后，轻量级收集用户反馈：

```json
{
  "config": {
    "wide_screen_mode": true
  },
  "header": {
    "template": "turquoise",
    "title": {
      "tag": "plain_text",
      "content": "💬 这个回答对你有帮助吗？"
    }
  },
  "elements": [
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "👍 有帮助"
          },
          "type": "primary",
          "value": {
            "action": "feedback_positive",
            "message_id": "msg_001"
          }
        },
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "👎 不太对"
          },
          "type": "default",
          "value": {
            "action": "feedback_negative",
            "message_id": "msg_001"
          }
        }
      ]
    }
  ]
}
```

---

## 5. 卡片交互处理

### 5.1 交互路由

```python
# 卡片交互路由表
CARD_ACTION_ROUTES = {
    # 策略管理
    "confirm_strategy": handle_confirm_strategy,
    "edit_strategy": handle_edit_strategy,
    "discard_strategy": handle_discard_strategy,
    
    # 回测相关
    "view_backtest_detail": handle_backtest_detail,
    "adjust_params": handle_adjust_params,
    
    # 行情预警
    "view_analysis": handle_view_analysis,
    "mute_alert": handle_mute_alert,
    
    # 报告
    "view_weekly_detail": handle_weekly_detail,
    
    # 反馈
    "feedback_positive": handle_feedback_positive,
    "feedback_negative": handle_feedback_negative,
}
```

### 5.2 交互处理流程

```
用户点击卡片按钮
    │
    ▼
飞书推送 card.action.trigger 事件
    │
    ▼
API Gateway → FeishuHandler
    │
    ├── 1. 解析 action value
    │   └── {action: "confirm_strategy", strategy_id: "strat_001"}
    │
    ├── 2. 路由到对应处理函数
    │
    ├── 3. 执行业务逻辑
    │   └── e.g., 将策略卡片状态设为"已确认"
    │
    └── 4. 更新卡片 (显示"已确认 ✅")
        └── PATCH /im/v1/messages/{message_id}
```

---

## 6. 主动推送机制

### 6.1 推送场景与频率

| 场景 | 触发条件 | 频率 | 推送方式 |
|------|---------|------|---------|
| 盘前策略 | 每日08:30 | 1次/天 | 卡片消息 |
| 行情预警 | 价格触及关注位 | 实时 | 卡片消息 |
| 教学确认 | 新策略提取完成 | 按需 | 卡片消息 |
| 反馈收集 | 深度对话后 | 2-3次/天 | 轻量卡片 |
| 交易偏差 | 检测到偏离策略 | 按需 | 文本消息 |
| 周报 | 每周日20:00 | 1次/周 | 卡片消息 |
| 蒸馏报告 | 蒸馏训练完成 | 1次/月 | 卡片消息 |

### 6.2 推送防骚扰规则

```
┌──────────────────────────────────────────────────────────┐
│                  推送防骚扰策略                            │
│                                                           │
│  1. 时间窗口                                              │
│  ├── 允许推送: 08:00 - 22:00                              │
│  └── 静默时段: 22:00 - 08:00 (仅行情预警可突破)          │
│                                                           │
│  2. 频率限制                                              │
│  ├── 同一品种预警: 最少间隔5分钟                          │
│  ├── 反馈收集: 每天最多3次                                │
│  └── 总推送: 每天最多10条 (预警除外)                     │
│                                                           │
│  3. 优先级排序                                            │
│  ├── P0 (立即推送): 行情触及止损位                        │
│  ├── P1 (5分钟内推送): 行情触及关注位                     │
│  ├── P2 (下一空闲推送): 教学确认、偏差提醒               │
│  └── P3 (批量推送): 周报、蒸馏报告                       │
└──────────────────────────────────────────────────────────┘
```

---

## 7. 技术实现

### 7.1 核心代码结构

```python
# src/feishu/bot.py

import lark_oapi as lark
from lark_oapi.api.im.v1 import *

class FeishuBot:
    """飞书Bot核心类"""
    
    def __init__(self, config: FeishuConfig):
        self.client = lark.Client.builder() \
            .app_id(config.app_id) \
            .app_secret(config.app_secret) \
            .build()
        self.handler = FeishuHandler(self.client)
    
    async def handle_event(self, event: dict) -> None:
        """处理飞书事件回调"""
        ...
    
    async def send_text(self, open_id: str, text: str) -> str:
        """发送文本消息，返回message_id"""
        ...
    
    async def send_card(self, open_id: str, card: dict) -> str:
        """发送交互卡片，返回message_id"""
        ...
    
    async def update_card(self, message_id: str, card: dict) -> None:
        """更新已发送的卡片"""
        ...
```

```python
# src/feishu/handler.py

class FeishuHandler:
    """飞书消息处理器"""
    
    async def handle_message(self, event: dict) -> None:
        """处理收到的消息"""
        # 1. 提取消息内容
        msg_type = event["message"]["message_type"]
        content = json.loads(event["message"]["content"])
        open_id = event["sender"]["sender_id"]["open_id"]
        
        # 2. 根据消息类型分发
        if msg_type == "text":
            text = content["text"]
            await self._handle_text(open_id, text)
        elif msg_type == "post":
            await self._handle_rich_text(open_id, content)
    
    async def handle_card_action(self, event: dict) -> None:
        """处理卡片交互"""
        action = event["action"]["value"]["action"]
        handler = CARD_ACTION_ROUTES.get(action)
        if handler:
            await handler(event)
    
    async def _handle_text(self, open_id: str, text: str) -> None:
        """处理文本消息"""
        # 构造MessageRequest → 交给AgentOrchestrator
        request = MessageRequest(
            user_id=open_id,
            content=text,
            message_type="text"
        )
        response = await self.orchestrator.handle_message(request)
        
        # 根据回复类型选择发送方式
        if response.message_type == "card":
            await self.bot.send_card(open_id, response.card_data)
        else:
            await self.bot.send_text(open_id, response.content)
        
        # 深度对话后推送反馈卡片
        if response.source == "cloud":
            await self._push_feedback_card(open_id, response.conversation_id)
```

### 7.2 卡片构建器

```python
# src/feishu/card_builder.py

class CardBuilder:
    """飞书卡片构建器"""
    
    @staticmethod
    def strategy_confirm(strategy: dict) -> dict:
        """构建策略确认卡片"""
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {"tag": "plain_text", "content": "📋 新策略卡片待确认"}
            },
            "elements": [
                # ... 见4.1节
            ]
        }
    
    @staticmethod
    def alert(symbol: str, price: float, level: float, 
              strategy_name: str) -> dict:
        """构建行情预警卡片"""
        ...
    
    @staticmethod
    def weekly_report(report: dict) -> dict:
        """构建周报卡片"""
        ...
    
    @staticmethod
    def feedback(message_id: str) -> dict:
        """构建反馈收集卡片"""
        ...
    
    @staticmethod
    def distill_report(result: dict) -> dict:
        """构建蒸馏训练报告卡片"""
        ...
```

### 7.3 签名验证

```python
# src/feishu/auth.py

import hashlib
import hmac

class FeishuAuth:
    """飞书签名验证"""
    
    def __init__(self, verification_token: str, encrypt_key: str):
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key
    
    def verify_signature(self, timestamp: str, nonce: str, 
                         body: str, signature: str) -> bool:
        """验证飞书事件签名"""
        content = timestamp + nonce + self.encrypt_key + body
        computed = hashlib.sha256(content.encode()).hexdigest()
        return hmac.compare_digest(computed, signature)
    
    def handle_challenge(self, event: dict) -> dict:
        """处理飞书URL验证"""
        if event.get("challenge"):
            return {"challenge": event["challenge"]}
        return None
```

---

## 8. 内网穿透配置

### 8.1 开发阶段：frp

```ini
# frpc.ini
[common]
server_addr = your-frp-server.com
server_port = 7000

[feishu-webhook]
type = http
local_ip = 127.0.0.1
local_port = 8000
custom_domains = trade-assistant.your-domain.com
```

### 8.2 开发阶段：Cloudflare Tunnel (推荐)

```bash
# 一键启动
cloudflared tunnel --url http://localhost:8000
```

优势：无需购买域名和服务器，Cloudflare自动分配域名

### 8.3 生产阶段

```
方案A: 继续使用frp/Cloudflare Tunnel (个人使用足够)
方案B: 部署轻量云服务器做反向代理
```

---

## 9. 错误处理

| 错误场景 | 处理策略 |
|---------|---------|
| 飞书API调用失败 | 重试3次，指数退避；失败后记录日志 |
| 签名验证失败 | 拒绝请求，记录可疑IP |
| 消息发送超时 | 降级为简单文本消息重试 |
| 卡片JSON格式错误 | 降级为文本消息发送 |
| 用户速率过快 | 合并处理，返回一条综合回复 |
| 本地模型不可用 | 自动切换到云端大模型，并通知用户 |

---

## 10. 测试策略

| 测试类型 | 内容 | 工具 |
|---------|------|------|
| 单元测试 | 签名验证、卡片构建、消息解析 | pytest |
| 集成测试 | 完整消息收发流程 | 飞书测试群 |
| 卡片预览 | 各类卡片渲染效果 | 飞书卡片搭建工具 |
| 压力测试 | 高频消息处理 | locust |
| 异常测试 | 网络断开、API错误等 | 手动模拟 |
