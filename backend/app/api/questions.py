"""
问题管理API路由 — 核心业务接口
提供问题的创建（SSE流式返回答案）、列表查询、详情查看、删除、反馈等功能。
这是Mirro最核心的业务入口，所有用户问题从这里进入系统。
"""
import uuid
import json
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.database import get_db
from app.models.schemas import QuestionCreate, QuestionResponse, QuestionDetail, AnswerResponse, AnswerWithQuestion, Source, SolutionStep, FeedbackCreate, FeedbackResponse
from app.services.ai_service import generate_answer, classify_question, generate_related_questions
from app.services.search_service import search_related_resources
from app.services.flowchart_service import validate_mermaid, generate_fallback_flowchart

router = APIRouter(prefix="/api/questions", tags=["问题管理"])


async def _stream_answer(question_id: str, content: str, category: str, conversation_id: str | None = None):
    """
    SSE流式返回答案的核心生成器
    业务逻辑：
    1. 先保存问题到数据库
    2. 同时启动分类和搜索后台任务（不阻塞主流程）
    3. 如果是多轮对话追问，则获取历史QA并拼接进LLM上下文
    4. 立即开始AI答案生成
    5. 逐阶段发送SSE事件：分类 → 正文 → 流程图 → 步骤 → 来源 → 完成
    6. 后台任务完成后更新分类和来源
    7. 前端根据event类型分别渲染不同区域

    SSE事件类型说明：
    - category:  问题分类结果（初始占位，后台分类完成后发送真实分类更新）
    - searching:  开始全网搜索
    - type:      答案类型（action=含步骤计划 / insight=纯深度分析），前端据此决定是否渲染步骤和流程图区域
    - content:   Markdown正文内容（逐块发送，前端拼接）
    - flowchart: Mermaid流程图（仅action类型且流程复杂时发送）
    - steps:     分步执行计划（仅action类型时发送，insight类型为空数组）
    - sources:   搜索来源引用
    - error:     发生错误（前端展示错误信息）
    - done:      全部完成，携带答案ID
    """
    now = datetime.now(timezone.utc).isoformat()

    # ===== 阶段0：保存问题 + 启动后台任务 =====
    try:
        db = await get_db()
        await db.execute(
            "INSERT INTO questions (id, content, category, conversation_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (question_id, content, category, conversation_id, now)
        )
        await db.commit()
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'message': f'数据库写入失败: {str(e)}'}, ensure_ascii=False)}\n\n"
        return

    # 启动后台任务：分类 + 搜索（与AI生成并发执行，不阻塞主流程）
    classify_task = asyncio.create_task(classify_question(content))
    search_task = asyncio.create_task(search_related_resources(content))

    # 阶段0.5：获取多轮对话历史（如果是追问）
    conversation_history = None
    if conversation_id:
        try:
            history_rows = await db.execute_fetchall(
                """SELECT q.content, a.content as answer_content
                   FROM questions q
                   LEFT JOIN answers a ON q.id = a.question_id
                   WHERE (q.id = ? OR q.conversation_id = ?) AND a.content IS NOT NULL
                   ORDER BY q.created_at ASC""",
                (conversation_id, conversation_id)
            )
            if history_rows:
                conversation_history = []
                for row in history_rows:
                    conversation_history.append({"role": "user", "content": row[0]})
                    if row[1]:
                        # 截断过长历史，每段最多保留2000字
                        truncated = row[1][:2000] + ("..." if len(row[1]) > 2000 else "")
                        conversation_history.append({"role": "assistant", "content": truncated})
        except Exception as e:
            print(f"[SSE] 获取对话历史失败: {e}")

    # 阶段1：发送初始分类结果（占位，后台分类完成后会发送更新）
    yield f"event: category\ndata: {category}\n\n"

    # 阶段2：通知前端开始全网搜索
    yield f"event: searching\ndata: 正在搜索全网案例...\n\n"

    # 阶段3：调用AI生成结构化答案（立即开始，不等待搜索/分类）
    try:
        ai_result = await generate_answer(content, history=conversation_history)
    except RuntimeError as e:
        yield f"event: error\ndata: {json.dumps({'message': f'AI服务暂时不可用，请稍后重试: {str(e)}'}, ensure_ascii=False)}\n\n"
        return
    except json.JSONDecodeError as e:
        yield f"event: error\ndata: {json.dumps({'message': 'AI返回格式异常，请重试'}, ensure_ascii=False)}\n\n"
        return
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'message': f'AI生成失败: {str(e)}'}, ensure_ascii=False)}\n\n"
        return

    # 阶段3.5：发送答案类型（前端据此决定是否渲染步骤/流程图区域）
    answer_type = ai_result.get("type", "insight")
    yield f"event: type\ndata: {answer_type}\n\n"

    # 阶段4：逐块发送Markdown正文（模拟流式打字机效果）
    # 按段落分割，每次发送一段，给前端时间渲染
    # 注意：段落内可能含 \n，需要替换为 \ndata: 符合SSE多行数据规范
    markdown_content = ai_result["content"]
    paragraphs = markdown_content.split("\n\n")
    for para in paragraphs:
        if para.strip():
            safe_data = para.strip().replace("\n", "\ndata: ")
            yield f"event: content\ndata: {safe_data}\n\n"

    # 阶段5：发送流程图（仅当AI生成了有效流程图时才发送）
    flowchart = ai_result.get("flowchart_mermaid", "")
    if flowchart and validate_mermaid(flowchart):
        yield f"event: flowchart\ndata: {flowchart}\n\n"
    elif flowchart and not validate_mermaid(flowchart):
        # AI 尝试画了但格式不对，用兜底（现在兜底返回空，即跳过）
        fallback = generate_fallback_flowchart(content)
        if fallback:
            yield f"event: flowchart\ndata: {fallback}\n\n"

    # 阶段6：发送分步执行计划
    steps = ai_result.get("steps", [])
    yield f"event: steps\ndata: {json.dumps(steps, ensure_ascii=False)}\n\n"

    # 阶段6.5：发送AI生成的相关推荐追问（与答案同一轮AI调用产出，零额外token）
    related_questions = ai_result.get("related_questions", [])
    if isinstance(related_questions, list) and related_questions:
        yield f"event: related_questions\ndata: {json.dumps(related_questions, ensure_ascii=False)}\n\n"

    # ===== 阶段7：收集后台任务结果 =====
    # AI内容已全部发送完毕，现在等待分类和搜索的后台结果

    # 7a. 获取真实分类
    try:
        real_category = await classify_task
    except Exception:
        real_category = category  # 分类失败，用占位值兜底

    # 7b. 更新数据库中问题的真实分类
    if real_category != category:
        try:
            await db.execute(
                "UPDATE questions SET category = ? WHERE id = ?",
                (real_category, question_id)
            )
            await db.commit()
        except Exception as e:
            print(f"[SSE] 分类更新失败: {e}")

    # 7c. 发送真实分类（前端会覆盖之前的占位值）
    yield f"event: category\ndata: {real_category}\n\n"

    # 7d. 获取搜索结果
    try:
        sources = await search_task
    except Exception:
        sources = []
        print(f"[SSE] 搜索任务异常，返回空结果")

    # 7e. 发送搜索来源
    yield f"event: sources\ndata: {json.dumps(sources, ensure_ascii=False)}\n\n"

    # ===== 阶段8：保存完整答案到数据库 =====
    answer_id = str(uuid.uuid4())
    try:
        await db.execute(
            """INSERT INTO answers (id, question_id, content, answer_type, flowchart_mermaid, steps, sources, related_questions, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                answer_id,
                question_id,
                markdown_content,
                answer_type,
                flowchart,
                json.dumps(steps, ensure_ascii=False),
                json.dumps(sources, ensure_ascii=False),
                json.dumps(related_questions, ensure_ascii=False),
                now
            )
        )
        await db.commit()
    except Exception as e:
        print(f"[SSE] 答案保存失败: {e}")

    # 阶段9：发送完成事件（携带问题和答案ID，前端用于跳转）
    yield f"event: done\ndata: {json.dumps({'question_id': question_id, 'answer_id': answer_id}, ensure_ascii=False)}\n\n"


@router.post("")
async def create_question(body: QuestionCreate):
    """
    提交新问题 → SSE流式返回AI解答全过程
    业务场景：用户在首页输入问题并提交，页面实时展示AI生成答案的过程。
    支持多轮对话：传入 conversation_id 时会加载历史QA拼接进LLM上下文。
    流式推送内容：分类→搜索来源→正文段落→流程图→步骤计划→完成通知
    """
    question_id = str(uuid.uuid4())
    category = "分析中..."  # 先占位，分类在流式过程中更新

    return StreamingResponse(
        _stream_answer(question_id, body.content, category, body.conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲，确保SSE实时推送
        }
    )


@router.get("")
async def list_questions(page: int = 1, size: int = 20, search: str = "", category: str = "", exclude: str = "") -> dict:
    """
    获取问题历史列表（分页 + 搜索 + 分类筛选 + 排除指定ID）
    业务场景：历史页面展示用户所有提问，按时间倒序排列。
    支持按关键词搜索问题内容、按分类筛选、以及排除指定问题ID（相关推荐用）。
    """
    db = await get_db()
    offset = (page - 1) * size

    # 动态构建WHERE条件
    conditions = []
    params: list = []

    if search.strip():
        conditions.append("content LIKE ?")
        params.append(f"%{search.strip()}%")

    if category.strip():
        conditions.append("category = ?")
        params.append(category.strip())

    if exclude.strip():
        conditions.append("id != ?")
        params.append(exclude.strip())

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # 查询问题总数（用于前端分页器）
    count_sql = f"SELECT COUNT(*) as count FROM questions {where_clause}"
    total_row = await db.execute_fetchall(count_sql, tuple(params))
    total = total_row[0][0] if total_row else 0

    # 查询当前页的问题列表，按创建时间倒序
    query_params = list(params) + [size, offset]
    query_sql = f"SELECT id, content, category, created_at FROM questions {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?"
    rows = await db.execute_fetchall(query_sql, tuple(query_params))

    questions = []
    for row in rows:
        questions.append(QuestionResponse(
            id=row[0],
            content=row[1],
            category=row[2],
            created_at=row[3]
        ).model_dump())

    return {"items": questions, "total": total, "page": page, "size": size}


@router.get("/stats")
async def get_stats() -> dict:
    """
    获取问题统计数据
    业务场景：统计看板页面的图表数据来源。返回分类分布和提问趋势。
    """
    db = await get_db()

    # 按分类统计问题数量（饼图数据）
    category_rows = await db.execute_fetchall(
        "SELECT category, COUNT(*) as count FROM questions GROUP BY category ORDER BY count DESC"
    )
    categories = [{"name": row[0] or "未分类", "count": row[1]} for row in category_rows]

    # 按日期统计提问数量（趋势图数据）
    date_rows = await db.execute_fetchall(
        "SELECT DATE(created_at) as date, COUNT(*) as count FROM questions GROUP BY DATE(created_at) ORDER BY date"
    )
    daily_trend = [{"date": row[0], "count": row[1]} for row in date_rows]

    # 总问题数
    total_row = await db.execute_fetchall("SELECT COUNT(*) FROM questions")
    total = total_row[0][0] if total_row else 0

    # 总答案数（解决率）
    answer_row = await db.execute_fetchall("SELECT COUNT(*) FROM answers")
    answered = answer_row[0][0] if answer_row else 0

    return {
        "total_questions": total,
        "total_answers": answered,
        "categories": categories,
        "daily_trend": daily_trend
    }


@router.get("/{question_id}")
async def get_question(question_id: str) -> QuestionDetail:
    """
    获取问题详情（含答案）
    业务场景：用户点击历史列表中的某条记录，或答案页直接访问时加载完整数据。
    """
    db = await get_db()

    # 查询问题
    row = await db.execute_fetchall(
        "SELECT id, content, category, created_at FROM questions WHERE id = ?",
        (question_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="问题不存在")

    question = QuestionResponse(
        id=row[0][0],
        content=row[0][1],
        category=row[0][2],
        created_at=row[0][3]
    )

    # 查询关联的答案
    answer = None
    answer_row = await db.execute_fetchall(
        "SELECT id, question_id, content, answer_type, flowchart_mermaid, steps, sources, related_questions, created_at FROM answers WHERE question_id = ?",
        (question_id,)
    )
    if answer_row:
        row_data = answer_row[0]
        # 解析JSON字符串
        answer_type = row_data[3] if len(row_data) > 3 and row_data[3] else "insight"
        steps_data = json.loads(row_data[5]) if row_data[5] else []
        sources_data = json.loads(row_data[6]) if row_data[6] else []
        related_questions_data = json.loads(row_data[7]) if len(row_data) > 7 and row_data[7] else []

        answer = AnswerResponse(
            id=row_data[0],
            question_id=row_data[1],
            type=answer_type,
            content=row_data[2] or "",
            flowchart_mermaid=row_data[4],
            steps=[SolutionStep(**s) for s in steps_data],
            sources=[Source(**s) for s in sources_data],
            related_questions=related_questions_data,
            created_at=row_data[8]
        )

    return QuestionDetail(
        id=question.id,
        content=question.content,
        category=question.category,
        created_at=question.created_at,
        answer=answer
    )


@router.get("/{question_id}/related")
async def get_related_questions(question_id: str) -> dict:
    """
    获取与当前问题相关的追问建议
    优先从数据库读取（AI生成答案时一并产出，零额外消耗），
    仅当旧数据无此字段时才降级调用AI实时生成。
    """
    db = await get_db()

    # 优先从 answers 表读取已缓存的相关推荐
    a_rows = await db.execute_fetchall(
        "SELECT related_questions, content FROM answers WHERE question_id = ?",
        (question_id,)
    )
    if a_rows and a_rows[0][0]:
        try:
            cached = json.loads(a_rows[0][0])
            if isinstance(cached, list) and cached:
                return {"related_questions": cached}
        except (json.JSONDecodeError, TypeError):
            pass

    # 降级：旧数据无缓存时，实时调用AI生成
    q_rows = await db.execute_fetchall(
        "SELECT content FROM questions WHERE id = ?",
        (question_id,)
    )
    if not q_rows:
        raise HTTPException(status_code=404, detail="问题不存在")

    question_content = q_rows[0][0]
    answer_content = a_rows[0][1] if a_rows else ""

    suggestions = await generate_related_questions(question_content, answer_content)

    # 回写缓存，下次访问直接读库
    if suggestions and a_rows:
        try:
            await db.execute(
                "UPDATE answers SET related_questions = ? WHERE question_id = ?",
                (json.dumps(suggestions, ensure_ascii=False), question_id)
            )
            await db.commit()
        except Exception as e:
            print(f"[相关推荐] 缓存回写失败: {e}")

    return {"related_questions": suggestions}


@router.delete("/{question_id}")
async def delete_question(question_id: str) -> dict:
    """
    删除问题及其答案
    业务场景：用户删除历史列表中的某条提问记录。
    数据库设置了CASCADE外键，删除问题会自动删除关联的答案。
    """
    db = await get_db()
    await db.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    await db.commit()
    return {"message": "已删除", "question_id": question_id}


@router.post("/{question_id}/feedback")
async def submit_feedback(question_id: str, body: FeedbackCreate) -> dict:
    """
    提交答案反馈（👍/👎）
    业务场景：用户对AI生成的答案质量进行评价，可选附加文字反馈。
    数据积累后可用于评估模型效果、优化prompt。
    """
    now = datetime.now(timezone.utc).isoformat()
    feedback_id = str(uuid.uuid4())
    db = await get_db()

    # 检查问题是否存在
    rows = await db.execute_fetchall("SELECT id FROM questions WHERE id = ?", (question_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="问题不存在")

    # 检查答案是否存在
    answer_rows = await db.execute_fetchall("SELECT id FROM answers WHERE id = ? AND question_id = ?", (body.answer_id, question_id))
    if not answer_rows:
        raise HTTPException(status_code=404, detail="答案不存在")

    try:
        await db.execute(
            """INSERT INTO feedback (id, question_id, answer_id, rating, comment, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (feedback_id, question_id, body.answer_id, body.rating, body.comment, now)
        )
        await db.commit()
    except Exception as e:
        print(f"[Feedback] 保存反馈失败: {e}")
        raise HTTPException(status_code=500, detail="反馈保存失败")

    return {"message": "反馈已提交", "feedback_id": feedback_id}


@router.get("/{question_id}/feedback")
async def get_feedback(question_id: str) -> dict:
    """
    获取某问题的反馈记录
    业务场景：前端加载答案详情时查询用户是否已提交过反馈。
    """
    db = await get_db()
    rows = await db.execute_fetchall(
        """SELECT id, question_id, answer_id, rating, comment, created_at
           FROM feedback WHERE question_id = ?""",
        (question_id,)
    )

    feedbacks = []
    for row in rows:
        feedbacks.append(FeedbackResponse(
            id=row[0],
            question_id=row[1],
            answer_id=row[2],
            rating=row[3],
            comment=row[4],
            created_at=row[5]
        ).model_dump())

    return {"feedbacks": feedbacks}
