"""路由意图分类 Prompt 模板"""

# 意图分类 Prompt
INTENT_CLASSIFICATION_PROMPT = """请判断以下用户消息的意图类别。

用户消息: {message}

可选意图:
- greeting: 问候/闲聊
- strategy_query: 查询已有策略
- rule_confirm: 确认交易规则
- knowledge_search: 搜索知识库内容
- strategy_analysis: 策略深度分析/推理
- teaching: 教学新策略/规则
- trade_review: 交易复盘/分析
- market_data: 查询行情数据
- general: 其他

只输出意图标签名称，不要输出其他内容。"""

# 复杂度评估 Prompt
COMPLEXITY_ASSESSMENT_PROMPT = """请评估以下用户消息的处理复杂度。

用户消息: {message}

可选复杂度:
- low: 简单查询/确认，可用固定规则或简短回答
- medium: 需要检索知识库或做简单推理
- high: 需要多步推理/深度分析/创造性回答

只输出复杂度标签，不要输出其他内容。"""
