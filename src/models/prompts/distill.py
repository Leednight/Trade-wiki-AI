"""蒸馏数据精炼 Prompt 模板 (Phase 2 使用)"""

# 思维链提取 Prompt
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

以JSON格式输出。
"""

# 风格标注 Prompt
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

以JSON格式输出。
"""
