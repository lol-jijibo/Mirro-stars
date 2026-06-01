"""
Mirro Pydantic 数据模型
定义前后端交互的数据结构，FastAPI自动基于这些模型生成API文档和请求校验。
"""
from pydantic import BaseModel, Field
from typing import Optional


# ========== 问题相关模型 ==========

class QuestionCreate(BaseModel):
    """
    用户提交问题的请求体
    业务场景：前端提问页面提交表单时发送此结构
    """
    content: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="用户提问的原始内容，最少5字最多500字",
        examples=["我25岁，想转行做程序员但零基础，应该怎么规划？"]
    )
    conversation_id: Optional[str] = Field(
        None,
        description="多轮对话的会话ID。传入此字段表示该问题是某次对话的追问，后端会将历史问答拼接进LLM上下文"
    )


class Source(BaseModel):
    """
    搜索来源引用
    业务场景：AI搜索全网资源后，每条引用展示标题+链接+摘要
    """
    title: str = Field(..., description="来源标题，如知乎问题标题、B站视频标题")
    url: str = Field(..., description="来源可点击链接")
    snippet: str = Field(..., description="来源内容摘要，帮助用户判断是否相关")


class SolutionStep(BaseModel):
    """
    解决方案的单个步骤
    业务场景：AI将复杂问题拆解为可执行的步骤序列，用户按顺序执行
    """
    step: int = Field(..., description="步骤序号，从1开始")
    title: str = Field(..., description="步骤名称，如'基础学习阶段'")
    description: str = Field(..., description="该步骤的详细说明")
    duration: str = Field(..., description="预计耗时，如'2-3个月'")


class AnswerResponse(BaseModel):
    """
    答案的完整响应结构
    业务场景：前端答案页一次性展示AI生成的完整方案
    """
    id: str = Field(..., description="答案唯一ID")
    question_id: str = Field(..., description="关联的问题ID")
    type: str = Field(default="insight", description="答案类型: action=含步骤计划, insight=纯深度分析")
    content: str = Field(..., description="Markdown格式的AI解答正文")
    flowchart_mermaid: Optional[str] = Field(None, description="Mermaid流程图语法，前端用mermaid.js渲染")
    steps: list[SolutionStep] = Field(default_factory=list, description="分步执行计划")
    sources: list[Source] = Field(default_factory=list, description="AI搜索引用的来源列表")
    related_questions: list[str] = Field(default_factory=list, description="AI生成的相关追问建议，在生成答案时一并产出")
    created_at: str = Field(..., description="生成时间")


class QuestionResponse(BaseModel):
    """
    问题的展示结构（不含答案详情，用于列表页）
    """
    id: str = Field(..., description="问题唯一ID")
    content: str = Field(..., description="提问内容")
    category: Optional[str] = Field(None, description="问题分类")
    created_at: str = Field(..., description="提问时间")


class QuestionDetail(BaseModel):
    """
    问题详情（含问题+答案，用于详情页）
    业务场景：用户点击历史列表中的某条记录时返回
    """
    id: str = Field(..., description="问题ID")
    content: str = Field(..., description="提问内容")
    category: Optional[str] = Field(None, description="问题分类")
    created_at: str = Field(..., description="提问时间")
    answer: Optional[AnswerResponse] = Field(None, description="关联的答案，可能为空（处理中）")


# ========== 搜索相关模型 ==========

class SearchRequest(BaseModel):
    """
    搜索请求
    业务场景：用户在答案页点"搜索更多案例"时触发额外搜索
    """
    query: str = Field(..., description="搜索关键词", min_length=2)
    max_results: int = Field(default=5, ge=1, le=10, description="返回结果数量上限")


class SearchResult(BaseModel):
    """
    单条搜索结果
    """
    title: str
    url: str
    snippet: str


class SearchResponse(BaseModel):
    """
    搜索响应
    """
    query: str = Field(..., description="原始搜索词")
    results: list[SearchResult] = Field(default_factory=list, description="搜索结果列表")


# ========== 反馈相关模型 ==========

class AnswerWithQuestion(BaseModel):
    """
    通过answer_id获取答案及其关联问题的结构
    业务场景：分享链接 /share/:answer_id 展示只读答案页
    """
    answer: AnswerResponse = Field(..., description="答案详情")
    question: QuestionResponse = Field(..., description="关联的问题信息")


class FeedbackCreate(BaseModel):
    """
    用户对答案的反馈
    业务场景：用户在答案详情页对AI回答质量进行打分（👍/👎），可选附加文字评论
    """
    answer_id: str = Field(..., description="被评价的答案ID")
    rating: int = Field(..., ge=-1, le=1, description="评分：1=好评(👍), -1=差评(👎), 0=中性")
    comment: Optional[str] = Field(None, max_length=500, description="可选的文字反馈，最多500字")


class FeedbackResponse(BaseModel):
    """
    反馈记录的响应结构
    """
    id: str = Field(..., description="反馈ID")
    question_id: str = Field(..., description="关联的问题ID")
    answer_id: str = Field(..., description="关联的答案ID")
    rating: int = Field(..., description="评分：1/-1/0")
    comment: Optional[str] = Field(None, description="文字反馈")
    created_at: str = Field(..., description="反馈时间")
