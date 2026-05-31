"""
问题管理API路由 — 核心业务接口
提供问题的创建（SSE流式返回答案）、列表查询、详情查看、删除等功能。
这是Mirro最核心的业务入口，所有用户问题从这里进入系统。
"""
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.database import get_db
from app.models.schemas import QuestionCreate, QuestionResponse, QuestionDetail, AnswerResponse, Source, SolutionStep
from app.services.ai_service import generate_answer, classify_question
from app.services.search_service import search_related_resources
from app.services.flowchart_service import validate_mermaid, generate_fallback_flowchart

router = APIRouter(prefix="/api/questions", tags=["问题管理"])


async def _stream_answer(question_id: str, content: str, category: str):
    """
    SSE流式返回答案的核心生成器
    业务逻辑：
    1. 先保存问题到数据库
    2. 逐阶段发送SSE事件：分类 → 搜索中 → 正文(逐字) → 流程图 → 步骤 → 来源 → 完成
    3. 前端根据event类型分别渲染不同区域

    SSE事件类型说明：
    - category:  问题分类结果
    - searching:  开始全网搜索
    - type:      答案类型（action=含步骤计划 / insight=纯深度分析），前端据此决定是否渲染步骤和流程图区域
    - content:   Markdown正文内容（逐块发送，前端拼接）
    - flowchart: Mermaid流程图（仅action类型且流程复杂时发送）
    - steps:     分步执行计划（仅action类型时发送，insight类型为空数组）
    - sources:   搜索来源引用
    - error:     发生错误（前端展示错误信息）
    - done:      全部完成，携带答案ID
    """
    # 先保存问题记录到数据库
    now = datetime.now(timezone.utc).isoformat()
    try:
        db = await get_db()
        await db.execute(
            "INSERT INTO questions (id, content, category, created_at) VALUES (?, ?, ?, ?)",
            (question_id, content, category, now)
        )
        await db.commit()
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'message': f'数据库写入失败: {str(e)}'}, ensure_ascii=False)}\n\n"
        return

    # 阶段1：发送分类结果
    yield f"event: category\ndata: {category}\n\n"

    # 阶段2：全网搜索相关资源（异步执行，不阻塞AI答案生成）
    yield f"event: searching\ndata: 正在搜索全网案例...\n\n"
    sources = await search_related_resources(content)
    yield f"event: sources\ndata: {json.dumps(sources, ensure_ascii=False)}\n\n"

    # 阶段3：调用AI生成结构化答案
    try:
        ai_result = await generate_answer(content)
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

    # 阶段7：保存完整答案到数据库
    answer_id = str(uuid.uuid4())
    try:
        await db.execute(
            """INSERT INTO answers (id, question_id, content, answer_type, flowchart_mermaid, steps, sources, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                answer_id,
                question_id,
                markdown_content,
                answer_type,
                flowchart,
                json.dumps(steps, ensure_ascii=False),
                json.dumps(sources, ensure_ascii=False),
                now
            )
        )
        await db.commit()
    except Exception as e:
        print(f"[SSE] 答案保存失败: {e}")

    # 阶段8：发送完成事件（携带问题和答案ID，前端用于跳转）
    yield f"event: done\ndata: {json.dumps({'question_id': question_id, 'answer_id': answer_id}, ensure_ascii=False)}\n\n"


@router.post("")
async def create_question(body: QuestionCreate):
    """
    提交新问题 → SSE流式返回AI解答全过程
    业务场景：用户在首页输入问题并提交，页面实时展示AI生成答案的过程。
    流式推送内容：分类→搜索来源→正文段落→流程图→步骤计划→完成通知
    """
    question_id = str(uuid.uuid4())
    category = "分析中..."  # 先占位，分类在流式过程中更新

    return StreamingResponse(
        _stream_answer(question_id, body.content, category),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲，确保SSE实时推送
        }
    )


@router.get("")
async def list_questions(page: int = 1, size: int = 20) -> dict:
    """
    获取问题历史列表（分页）
    业务场景：历史页面展示用户所有提问，按时间倒序排列。
    """
    db = await get_db()
    offset = (page - 1) * size

    # 查询问题总数（用于前端分页器）
    total_row = await db.execute_fetchall("SELECT COUNT(*) as count FROM questions")
    total = total_row[0][0] if total_row else 0

    # 查询当前页的问题列表，按创建时间倒序
    rows = await db.execute_fetchall(
        "SELECT id, content, category, created_at FROM questions ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (size, offset)
    )

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
        "SELECT id, question_id, content, answer_type, flowchart_mermaid, steps, sources, created_at FROM answers WHERE question_id = ?",
        (question_id,)
    )
    if answer_row:
        row_data = answer_row[0]
        # 解析steps和sources的JSON字符串
        answer_type = row_data[3] if len(row_data) > 3 and row_data[3] else "insight"
        steps_data = json.loads(row_data[5]) if row_data[5] else []
        sources_data = json.loads(row_data[6]) if row_data[6] else []

        answer = AnswerResponse(
            id=row_data[0],
            question_id=row_data[1],
            type=answer_type,
            content=row_data[2] or "",
            flowchart_mermaid=row_data[4],
            steps=[SolutionStep(**s) for s in steps_data],
            sources=[Source(**s) for s in sources_data],
            created_at=row_data[7]
        )

    return QuestionDetail(
        id=question.id,
        content=question.content,
        category=question.category,
        created_at=question.created_at,
        answer=answer
    )


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
