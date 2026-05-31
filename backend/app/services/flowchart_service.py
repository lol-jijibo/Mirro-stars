"""
流程图服务模块 — 解决方案可视化
负责将AI生成的文本方案转化为Mermaid流程图语法。
当前版本主要由AI直接生成Mermaid，此服务提供兜底和验证逻辑。
（MVP阶段：流程图由ai_service在一次LLM调用中直接生成，此模块为后续扩展预留）
"""


def validate_mermaid(mermaid_text: str) -> bool:
    """
    验证Mermaid语法是否基本合法
    业务场景：AI生成的Mermaid可能存在语法问题，前端渲染前做基本校验。
    检查项：是否以graph开头、是否包含箭头语法
    """
    if not mermaid_text or len(mermaid_text.strip()) < 10:
        return False
    # 基本检查：包含Mermaid流程图关键字
    text = mermaid_text.strip()
    valid_starts = ["graph TD", "graph LR", "graph TB", "graph RL", "flowchart TD", "flowchart LR"]
    return any(text.startswith(start) for start in valid_starts) and "-->" in text


def generate_fallback_flowchart(question: str) -> str:
    """
    兜底流程图
    业务场景：当AI未能生成有效的Mermaid语法时，不再强制展示一个通用流程图。
    通用模板往往与用户的具体问题脱节，反而降低体验。返回空字符串，前端自行隐藏流程图区域。
    """
    return ""
