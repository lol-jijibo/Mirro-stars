/**
 * Mirro 前端类型定义
 * 业务场景：统一管理前后端数据结构，确保类型安全。
 * 与后端的 Pydantic schemas 保持一致。
 */

// ========== 问题相关类型 ==========

/** 用户提交问题的请求体 */
export interface QuestionCreate {
  content: string
  conversation_id?: string  // 多轮对话的会话ID，传入此字段表示追问
  clarification_context?: string  // 澄清向导收集的补充信息，只参与AI生成
}

/** 问题列表项（不含答案详情） */
export interface QuestionResponse {
  id: string
  content: string
  category: string | null
  created_at: string
}

/** 通过answer_id获取的答案+问题组合（分享页用） */
export interface AnswerWithQuestion {
  answer: AnswerResponse
  question: QuestionResponse
}

/** 搜索来源引用 */
export interface Source {
  title: string
  url: string
  snippet: string
}

/** 解决方案的单个步骤 */
export interface SolutionStep {
  step: number
  title: string
  description: string
  duration: string
}

/** 答案顶部行动摘要 */
export interface ActionSummary {
  conclusion: string
  first_action: string
  timeframe: string
  risk: string
  fit_for: string
}

/** AI生成的完整答案 */
export interface AnswerResponse {
  id: string
  question_id: string
  type: 'action' | 'insight'
  content: string
  flowchart_mermaid: string | null
  steps: SolutionStep[]
  sources: Source[]
  action_summary: ActionSummary | null
  related_questions: string[]
  created_at: string
}

/** 问题详情（问题 + 答案） */
export interface QuestionDetail {
  id: string
  content: string
  category: string | null
  created_at: string
  answer: AnswerResponse | null
}

// ========== 搜索相关类型 ==========

/** 搜索请求 */
export interface SearchRequest {
  query: string
  max_results: number
}

/** 单条搜索结果 */
export interface SearchResult {
  title: string
  url: string
  snippet: string
}

/** 搜索响应 */
export interface SearchResponse {
  query: string
  results: SearchResult[]
}

// ========== 统计相关类型 ==========

/** 分类统计项 */
export interface CategoryStat {
  name: string
  count: number
}

/** 每日趋势项 */
export interface DailyTrend {
  date: string
  count: number
}

/** 统计数据概览 */
export interface StatsOverview {
  total_questions: number
  total_answers: number
  categories: CategoryStat[]
  daily_trend: DailyTrend[]
}

// ========== SSE流式事件类型 ==========

/** SSE事件类型：后端推送的不同阶段的数据 */
export type SSEEventType =
  | 'category'          // 问题分类结果
  | 'searching'         // 正在搜索提示
  | 'type'              // 答案类型: action=含步骤计划 / insight=纯深度分析
  | 'action_summary'    // 答案顶部行动摘要
  | 'content'           // Markdown正文段落
  | 'flowchart'         // Mermaid流程图
  | 'steps'             // 分步执行计划
  | 'related_questions' // AI生成的相关追问建议
  | 'sources'           // 搜索来源列表
  | 'done'              // 全部完成

/** SSE事件数据 */
export interface SSEEvent {
  type: SSEEventType
  data: string
}

/** SSE完成事件携带的ID信息 */
export interface SSEDonePayload {
  question_id: string
  answer_id: string
}

// ========== 反馈相关类型 ==========

/** 提交反馈的请求体 */
export interface FeedbackCreate {
  answer_id: string
  rating: number  // 1=好评, -1=差评, 0=中性
  comment?: string
}

/** 反馈记录 */
export interface FeedbackResponse {
  id: string
  question_id: string
  answer_id: string
  rating: number
  comment: string | null
  created_at: string
}
