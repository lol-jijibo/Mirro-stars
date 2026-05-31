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
