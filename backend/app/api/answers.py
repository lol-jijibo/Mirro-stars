"""
答案相关API路由
提供通过答案ID获取答案详情的接口（用于分享功能）。
"""
import json
from fastapi import APIRouter, HTTPException
from app.models.database import get_db
from app.models.schemas import AnswerResponse, QuestionResponse, AnswerWithQuestion, Source, SolutionStep

router = APIRouter(prefix="/api/answers", tags=["答案管理"])


@router.get("/{answer_id}")
async def get_answer_by_id(answer_id: str) -> AnswerWithQuestion:
    """
    根据答案ID获取答案及其关联的问题
    业务场景：分享链接 /share/:answer_id 展示只读答案页，
    前端通过此接口获取答案内容和问题信息。
    """
    db = await get_db()

    # 查询答案
    answer_rows = await db.execute_fetchall(
        """SELECT id, question_id, content, answer_type, flowchart_mermaid, steps, sources, related_questions, created_at
           FROM answers WHERE id = ?""",
        (answer_id,)
    )
    if not answer_rows:
        raise HTTPException(status_code=404, detail="答案不存在")

    row = answer_rows[0]
    answer_type = row[3] if row[3] else "insight"
    steps_data = json.loads(row[5]) if row[5] else []
    sources_data = json.loads(row[6]) if row[6] else []
    related_questions_data = json.loads(row[7]) if len(row) > 7 and row[7] else []

    answer = AnswerResponse(
        id=row[0],
        question_id=row[1],
        type=answer_type,
        content=row[2] or "",
        flowchart_mermaid=row[4],
        steps=[SolutionStep(**s) for s in steps_data],
        sources=[Source(**s) for s in sources_data],
        related_questions=related_questions_data,
        created_at=row[8]
    )

    # 查询关联的问题
    question_rows = await db.execute_fetchall(
        "SELECT id, content, category, created_at FROM questions WHERE id = ?",
        (answer.question_id,)
    )
    if not question_rows:
        raise HTTPException(status_code=404, detail="关联问题不存在")

    q = question_rows[0]
    question = QuestionResponse(
        id=q[0],
        content=q[1],
        category=q[2],
        created_at=q[3]
    )

    return AnswerWithQuestion(answer=answer, question=question)
