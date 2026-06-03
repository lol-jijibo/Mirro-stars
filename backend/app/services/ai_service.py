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
MAX_JSON_RETRIES = 2     # JSON解析失败时的最大重试次数


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


def _repair_and_parse_json(raw_text: str) -> dict:
    """
    从LLM原始输出中提取并修复JSON。
    LLM（尤其是DeepSeek等模型）在多轮对话长上下文场景下容易产出格式异常的JSON：
    - 在JSON前后加解释文字
    - JSON内部字符串含未转义的换行符或引号
    - 数组/对象末尾多余的逗号（trailing comma）
    - Markdown代码块包裹

    此函数逐层尝试解析，从宽松到激进，确保尽可能恢复有效数据。
    如果所有尝试都失败，抛出 JSONDecodeError 让调用方决定是否重试。
    """
    text = raw_text.strip()

    # 第1层：去掉 ```json ... ``` 包裹
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1).strip()

    # 第2层：定位最外层 { } 边界
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end <= start:
        raise json.JSONDecodeError("未找到有效的JSON对象边界", text, 0)

    json_candidate = text[start:end + 1]

    # 第3层：直接尝试解析（大多数正常情况走这里）
    try:
        return json.loads(json_candidate)
    except json.JSONDecodeError:
        pass

    # 第4层：移除 trailing commas（LLM常见错误：数组/对象末尾多余逗号）
    repaired = re.sub(r',\s*([}\]])', r'\1', json_candidate)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # 第5层：修复字符串值内未转义的换行符
    # LLM有时在JSON字符串值中直接插入真实换行而非\n转义
    # 策略：找到所有字符串值，将其中的换行替换为\\n
    def _escape_newlines_in_strings(s: str) -> str:
        """在JSON字符串值内部转义未转义的换行符"""
        result = []
        in_string = False
        escape_next = False
        for ch in s:
            if escape_next:
                result.append(ch)
                escape_next = False
                continue
            if ch == '\\':
                result.append(ch)
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                result.append(ch)
                continue
            if in_string and ch == '\n':
                result.append('\\n')
                continue
            if in_string and ch == '\r':
                result.append('\\r')
                continue
            if in_string and ch == '\t':
                result.append('\\t')
                continue
            result.append(ch)
        return ''.join(result)

    repaired = _escape_newlines_in_strings(repaired)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # 第6层：尝试用正则提取各个顶层字段（最后手段）
    # 如果LLM返回了大部分有效JSON但有小错误，尝试逐字段提取
    result = _extract_fields_fallback(json_candidate)
    if result:
        print(f"[AI服务] JSON解析使用兜底字段提取，原始文本前200字符: {raw_text[:200]}")
        return result

    # 所有尝试都失败，保存原始文本用于调试，然后抛出异常
    print(f"[AI服务] JSON解析完全失败，原始返回前500字符: {raw_text[:500]}")
    raise json.JSONDecodeError(
        f"所有JSON修复策略均失败，原始文本前200字符: {raw_text[:200]}",
        raw_text, 0
    )


def _extract_fields_fallback(text: str) -> dict | None:
    """
    兜底方案：当JSON修复全部失败时，用正则逐字段提取。
    适用于LLM返回了"接近JSON"但有小语法错误（如key未加引号等）的场景。
    返回 None 表示无法提取有效数据。
    """
    result: dict = {}

    # 提取 type
    type_match = re.search(r'"type"\s*:\s*"(action|insight)"', text)
    result["type"] = type_match.group(1) if type_match else "insight"

    # 提取 content（核心字段，必须存在）
    # content 通常是多行文本，夹在 "content": " 和下一个顶层字段之间
    content_match = re.search(
        r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL
    )
    if not content_match:
        # 尝试匹配跨行的content：从 "content": " 到 ", "flowchart 或 ", "steps 或末尾
        content_match = re.search(
            r'"content"\s*:\s*"([\s\S]*?)"\s*(?:,\s*"(?:flowchart_mermaid|steps|related_questions|type|action_summary)|\s*\})',
            text
        )
    if content_match:
        result["content"] = content_match.group(1)
    else:
        # content 是核心字段，提取不到则整体失败
        return None

    # 提取 flowchart_mermaid
    fc_match = re.search(r'"flowchart_mermaid"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    result["flowchart_mermaid"] = fc_match.group(1) if fc_match else ""

    # 提取 steps（数组）
    steps_match = re.search(r'"steps"\s*:\s*(\[[\s\S]*?\])', text)
    if steps_match:
        try:
            result["steps"] = json.loads(steps_match.group(1))
        except json.JSONDecodeError:
            result["steps"] = []
    else:
        result["steps"] = []

    # 提取 action_summary（子对象）
    as_match = re.search(r'"action_summary"\s*:\s*(\{[\s\S]*?\})', text)
    if as_match:
        try:
            # 清理子对象中的trailing commas
            as_text = re.sub(r',\s*}', '}', as_match.group(1))
            result["action_summary"] = json.loads(as_text)
        except json.JSONDecodeError:
            result["action_summary"] = None
    else:
        result["action_summary"] = None

    # 提取 related_questions（字符串数组）
    rq_match = re.search(r'"related_questions"\s*:\s*(\[[\s\S]*?\])', text)
    if rq_match:
        try:
            result["related_questions"] = json.loads(rq_match.group(1))
        except json.JSONDecodeError:
            result["related_questions"] = []
    else:
        result["related_questions"] = []

    # 至少要有 content 才算成功
    return result if result.get("content") else None


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
        "steps": [{"step": 1, "title": "...", "description": "...", "duration": "..."}],
        "action_summary": {
            "conclusion": "...",
            "first_action": "...",
            "timeframe": "...",
            "risk": "...",
            "fit_for": "..."
        }
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

### action_summary（必填）
为答案生成一个可立即阅读的顶部摘要，帮助用户先抓住重点再看全文：
- conclusion: 核心结论，用2-3句话直击问题本质
- first_action: 用户现在最应该先做的一件事，要具体可执行
- timeframe: 整体建议周期或见效时间，如"1周内先验证方向，1-3个月持续推进"
- risk: 最需要注意的风险或误区
- fit_for: 该方案最适合的人群或场景

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
  "action_summary": {
    "conclusion": "...",
    "first_action": "...",
    "timeframe": "...",
    "risk": "...",
    "fit_for": "..."
  },
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

    # 用于JSON解析重试的消息基础（重试时会追加格式纠正提示）
    base_messages = list(messages)

    last_raw_text = ""
    for json_attempt in range(MAX_JSON_RETRIES + 1):
        # 重试时降低temperature以提高格式稳定性
        temperature = 0.7 if json_attempt == 0 else 0.3

        response = await _retry_call(
            client=client,
            messages=messages,
            temperature=temperature,
            max_tokens=4000,
        )

        raw_text = response.choices[0].message.content.strip()
        last_raw_text = raw_text

        try:
            result = _repair_and_parse_json(raw_text)
            return {
                "type": result.get("type", "insight"),
                "content": result.get("content", ""),
                "flowchart_mermaid": result.get("flowchart_mermaid", ""),
                "steps": result.get("steps", []),
                "action_summary": result.get("action_summary"),
                "related_questions": result.get("related_questions", []),
            }
        except json.JSONDecodeError as e:
            if json_attempt < MAX_JSON_RETRIES:
                print(f"[AI服务] JSON解析失败(尝试{json_attempt+1}/{MAX_JSON_RETRIES+1})，将重试: {e}")
                # 在消息末尾追加格式纠正提示，让模型重新生成
                messages = list(base_messages) + [
                    {"role": "assistant", "content": raw_text[:500]},
                    {"role": "user", "content": (
                        "你上面的回复格式有误，无法解析为JSON。请严格只输出要求的JSON对象，不要在前面或后面加任何解释文字。"
                        "特别注意：JSON中所有字符串值内的双引号必须用反斜杠转义（\\\"），换行符必须写为\\\\n而非真实换行。"
                        "请重新输出完整JSON。"
                    )},
                ]
                # 重试前短暂等待
                await asyncio.sleep(0.5)
            else:
                # 所有JSON重试都失败了
                print(f"[AI服务] JSON解析最终失败，原始返回前1000字符: {last_raw_text[:1000]}")
                raise


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
    分类体系：8个类别覆盖年轻人常见问题领域。
    """
    client = _get_client()

    system_prompt = """你是一个问题分类专家。请将用户问题归入以下8个类别之一，只回复类别名称。

## 分类标准（含典型示例）

1. **职业发展** — 求职、面试、转行、跳槽、薪资谈判、职业规划、副业、创业、职场人际关系、行业选择
   示例："如何准备产品经理面试？"、"要不要从大厂跳去创业公司？"

2. **情感关系** — 恋爱、婚姻、家庭关系、友情、暧昧、分手、相亲、亲密关系沟通
   示例："异地恋怎么维持？"、"父母催婚怎么办？"

3. **个人成长** — 学习方法、时间管理、习惯养成、思维提升、情绪管理、自我认知、人生规划
   示例："如何克服拖延症？"、"怎样建立批判性思维？"

4. **理财规划** — 投资、储蓄、买房、保险、税务、消费观、负债管理
   示例："月入1万怎么理财？"、"买房还是租房？"

5. **健康生活** — 运动健身、饮食营养、睡眠、心理健康、医疗、养生、皮肤护理
   示例："如何改善失眠？"、"增肌期间怎么吃？"

6. **社交技巧** — 沟通表达、人脉搭建、社交焦虑、公共演讲、谈判说服、网络社交
   示例："怎么在饭局上不冷场？"、"如何优雅地拒绝别人？"

7. **技术学习** — 编程开发、AI/机器学习、工程技术、工具软件、技术架构、开源项目、科技趋势
   示例："什么是Harness工程？"、"React和Vue怎么选？"、"如何入门大模型开发？"

8. **其他** — 以上7类都无法覆盖的问题（如纯娱乐八卦、纯粹的好奇问答、无法归类的抽象问题等）
   注意：只有在确实不属于前7类时才选此项，不要偷懒。

## 分类原则
- 优先选最匹配的那个类别，不要犹豫
- 技术、编程、工程、AI类问题 → 技术学习
- 学习/自我提升但非技术类 → 个人成长
- 工作中的关系处理 → 职业发展
- 只有真正无法归类时才选"其他\""""

    response = await _retry_call(
        client=client,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分类以下问题（只回复类别名）：\n{question}"},
        ],
        temperature=0.3,
        max_tokens=20,
    )

    category = response.choices[0].message.content.strip()
    # 清理可能的标点和空格
    category = category.replace("：", "").replace(":", "").strip()

    valid_categories = ["职业发展", "情感关系", "个人成长", "理财规划", "健康生活", "社交技巧", "技术学习", "其他"]
    if category in valid_categories:
        return category

    # 模糊匹配：LLM 可能返回了带序号或描述的内容
    for vc in valid_categories:
        if vc in category:
            return vc

    return "其他"
