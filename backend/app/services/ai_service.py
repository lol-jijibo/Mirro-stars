"""
AI服务模块 — 核心业务大脑
负责调用LLM生成结构化答案、解决方案流程图和分步执行计划。
使用 OpenAI 兼容接口，支持切换不同模型提供商（OpenAI/Claude/DeepSeek等）。
"""
import asyncio
import json
import re
from openai import AsyncOpenAI, APIError, APITimeoutError, APIConnectionError
from app.core.config import settings

# 重试配置
MAX_RETRIES = 3          # 最大重试次数
RETRY_BACKOFF = 1.5      # 重试退避倍率（1s → 1.5s → 2.25s）
REQUEST_TIMEOUT = 60.0   # 单次请求超时（秒）


def _get_client() -> AsyncOpenAI:
    """
    初始化AI客户端
    业务场景：根据配置的LLM提供商创建对应的客户端实例。
    通过LLM_BASE_URL支持兼容OpenAI接口的其他服务（如DeepSeek、通义千问）。
    """
    kwargs = {
        "api_key": settings.LLM_API_KEY,
        "timeout": REQUEST_TIMEOUT,
        "max_retries": 0,  # 关闭SDK内置重试，我们自己控制重试逻辑
    }
    if settings.LLM_BASE_URL:
        kwargs["base_url"] = settings.LLM_BASE_URL
    return AsyncOpenAI(**kwargs)


def _is_retryable_error(error: Exception) -> bool:
    """
    判断错误是否可重试
    502/503/504 是网关/服务暂时不可用，重试通常能恢复。
    网络连接错误、超时也可重试。
    """
    if isinstance(error, APITimeoutError):
        return True
    if isinstance(error, APIConnectionError):
        return True
    if isinstance(error, APIError):
        # 5xx 服务端错误可重试，4xx 客户端错误不可重试
        status = getattr(error, "status_code", None)
        if status is not None and 500 <= status < 600:
            return True
    # 检查嵌套的 HTTP 状态码（某些 SDK 版本用不同方式暴露）
    status = getattr(error, "status_code", None) or getattr(error, "http_status", None)
    if status is not None and 500 <= status < 600:
        return True
    return False


async def _retry_call(client: AsyncOpenAI, messages: list, temperature: float, max_tokens: int):
    """
    带指数退避的LLM API调用
    业务场景：502/503等临时故障自动重试，提升服务可用性。
    """
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except (APIError, APITimeoutError, APIConnectionError) as e:
            last_error = e
            if not _is_retryable_error(e):
                raise  # 4xx 错误不重试，直接抛出
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF ** attempt
                print(f"[AI服务] API调用失败(尝试 {attempt+1}/{MAX_RETRIES})，{wait:.1f}s后重试: {e}")
                await asyncio.sleep(wait)
            else:
                print(f"[AI服务] API调用失败，已达最大重试次数({MAX_RETRIES}): {e}")

    # 所有重试都失败了
    raise RuntimeError(f"AI服务调用失败，已重试{MAX_RETRIES}次，最后错误: {last_error}")


async def generate_answer(question: str, history: list[dict] | None = None) -> dict:
    """
    核心业务方法：根据用户问题生成结构化答案
    一次LLM调用，智能判断问题类型后产出对应结构的答案。

    问题分为两类：
    - 行动型（action）：需要分步执行方案 → 输出正文 + 步骤 + 可选流程图
    - 认知型（insight）：只需要深度分析见解 → 只输出正文，步骤和流程图留空

    参数:
        question: 用户当前提问
        history: 多轮对话的历史问答对，格式为 [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

    返回格式：
    {
        "type": "action" | "insight",
        "content": "Markdown格式的解答正文",
        "flowchart_mermaid": "Mermaid语法字符串或空",
        "steps": [{"step": 1, "title": "...", "description": "...", "duration": "..."}]
    }
    """
    client = _get_client()

    # 系统提示词 — 定义AI的角色和输出规范
    system_prompt = """你是一个年轻人问题解决专家"Mirro"。你的任务是为年轻人（18-35岁）遇到的各类问题提供深度、有见地的解答。

## 第一步：判断问题类型

在回答之前，先判断用户的问题属于哪种类型：

- **action（行动型）**：用户需要一个可执行的方案。例如：转行规划、学习路线、健身计划、理财步骤、项目管理、技能提升路径、搬家流程、签证办理等。
- **insight（认知型）**：用户想理解某个问题、获得见解或建议。例如：情感困惑、职业迷茫、人生选择、心理困扰、观点讨论、人际关系分析、抽象思辨等。

## 第二步：根据类型组织回答

### content（必填）— Markdown正文

无论哪种类型，都要把问题讲透：

- 先给出核心结论或关键洞察（2-3句话，直击要害）
- 然后展开深度分析：
  - **认知型问题**：挖掘深层原因、提供多个视角（正反/利弊/不同立场）、援引相关心理学/社会学常识、给出务实建议。像一位有见识的朋友在和你深度聊天，不仅告诉你"是什么"，更要讲清楚"为什么"和"然后呢"。
  - **行动型问题**：说明每一步的"为什么"而不只是"做什么"，帮用户理解背后的逻辑。标明优先级和关键里程碑。
- 语言亲切但有深度，篇幅不限，把问题讲透为止，宁可详细不要敷衍
- 适当使用小标题、列表等Markdown格式增强可读性

### type（必填）
根据第一步的判断，返回 "action" 或 "insight"

### steps（仅 action 类型填写，insight 类型返回空数组 []）
为行动型问题设计3-6个分步执行计划，每个步骤包含：
- step: 步骤序号（从1开始）
- title: 阶段名称（如"准备期"、"行动期"）
- description: 该阶段具体要做什么，以及为什么要这么做（2-3句话）
- duration: 预计耗时（如"1-2周"、"3个月"）

### flowchart_mermaid（可选，不适配时返回空字符串 ""）
仅当问题有明确的多步骤决策/操作流程时才需要流程图。要求：
- 节点内容紧扣用户的具体问题，不要画泛泛的"发现问题→分析→解决"模板
- 从用户当前处境出发，经过3-6个关键决策点或行动节点
- 每个节点用中文短句描述（不超过10个字）
- 格式示例：graph TD\\n    A[具体现状] --> B[第一步行动] --> C[第二个节点] --> D[预期成果]
- 认知型问题、情感咨询、观点讨论等不需要流程图的，直接返回 ""

### related_questions（必填）
根据当前问题和你的回答，生成3个真正相关的深度追问建议，帮用户继续探索：
- 从不同角度切入（实操层面、原理层面、延伸场景、风险注意事项等）
- 每个问题简短精炼（15-30字），用中文自然表达
- 问题应该引导更深入的思考或行动，而不是重复原问题

输出必须严格符合以下JSON格式，不要在JSON外加任何文字：
{
  "type": "action",
  "content": "...Markdown...",
  "flowchart_mermaid": "graph TD\\n    A[...] --> B[...]",
  "steps": [
    {"step": 1, "title": "...", "description": "...", "duration": "..."}
  ],
  "related_questions": ["角度一的追问？", "角度二的追问？", "角度三的追问？"]
}"""

    # 构建消息列表：system prompt + 历史对话 + 当前问题
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    response = await _retry_call(
        client=client,
        messages=messages,
        temperature=0.7,
        max_tokens=4000,
    )

    # 解析LLM返回的JSON字符串
    raw_text = response.choices[0].message.content.strip()

    # 尝试提取JSON（LLM有时会在JSON外加markdown代码块标记）
    json_text = raw_text
    # 去掉可能的 ```json ... ``` 包裹
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_text)
    if match:
        json_text = match.group(1)
    else:
        # 尝试直接找到 { 和 }
        start = raw_text.find('{')
        end = raw_text.rfind('}') + 1
        if start != -1 and end > start:
            json_text = raw_text[start:end]

    result = json.loads(json_text)
    return {
        "type": result.get("type", "insight"),
        "content": result.get("content", ""),
        "flowchart_mermaid": result.get("flowchart_mermaid", ""),
        "steps": result.get("steps", []),
        "related_questions": result.get("related_questions", []),
    }


async def generate_related_questions(question: str, answer_content: str) -> list[str]:
    """
    根据当前问答内容，通过AI生成3个真正相关的追问建议。
    业务场景：答案页底部"相关推荐"区域，帮用户发现值得继续探索的问题方向。

    与简单的数据库分类筛选不同，此方法通过LLM理解问答语义后生成
    与当前话题真正相关的追问，而不是同一大类下的其他历史提问。
    """
    client = _get_client()

    prompt = f"""你是一个帮助用户深入探索问题的助手。请根据以下问答内容，生成3个与当前话题真正相关的追问建议。

要求：
- 从不同角度切入，角度要多样化（比如：实操层面、原理层面、延伸场景、风险注意事项等）
- 每个问题简短精炼（15-30字）
- 用中文提问，语言自然像朋友间的对话
- 问题应该引导更深入的思考或行动，而不是重复原问题

用户的问题：{question}

AI的回答摘要：{answer_content[:2000]}

请只返回一个JSON字符串数组，不要加其他内容。例如：["如何准备面试中的行为问题？", "转行到互联网需要多长时间？", "没有相关经验怎么破局？"]"""

    response = await _retry_call(
        client=client,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300,
    )

    raw = response.choices[0].message.content.strip()
    # 提取JSON数组
    match = re.search(r'\[([\s\S]*?)\]', raw)
    if match:
        try:
            parsed = json.loads(f"[{match.group(1)}]")
            if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                return parsed[:5]  # 最多5个
        except json.JSONDecodeError:
            pass

    print(f"[AI服务] 解析相关推荐失败，原始返回: {raw[:200]}")
    return []


async def classify_question(question: str) -> str:
    """
    对用户问题进行自动分类
    业务场景：历史列表中展示分类标签，统计看板中按分类汇总。
    分类体系：职业发展 / 情感关系 / 个人成长 / 理财规划 / 健康生活 / 社交技巧 / 其他
    """
    client = _get_client()

    prompt = f"""请对以下用户问题进行分类，只返回分类名称，不要返回其他内容。

分类选项：职业发展、情感关系、个人成长、理财规划、健康生活、社交技巧、其他

用户问题：{question}

分类："""

    response = await _retry_call(
        client=client,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=20,
    )

    category = response.choices[0].message.content.strip()
    # 确保返回的分类在预设范围内
    valid_categories = ["职业发展", "情感关系", "个人成长", "理财规划", "健康生活", "社交技巧", "其他"]
    return category if category in valid_categories else "其他"
