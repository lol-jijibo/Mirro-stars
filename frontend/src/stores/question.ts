/**
 * Pinia 问题状态管理
 * 管理当前正在生成中的答案状态（SSE流式数据缓存）。
 * 业务场景：用户在答案页等待AI生成时，store暂存所有SSE片段，
 * 生成完成后可以从store读取完整数据，也可以从后端API获取持久化数据。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SolutionStep, Source } from '@/types'

export const useQuestionStore = defineStore('question', () => {
  // ========== 流式生成状态（SSE过程中实时更新） ==========

  /** 当前正在生成的答案Markdown正文（逐段累加） */
  const streamingContent = ref('')

  /** 当前问题分类 */
  const streamingCategory = ref('')

  /** 答案类型：action=含步骤计划 / insight=纯深度分析 */
  const streamingType = ref<'action' | 'insight'>('insight')

  /** Mermaid流程图语法 */
  const streamingFlowchart = ref('')

  /** 分步执行计划 */
  const streamingSteps = ref<SolutionStep[]>([])

  /** 搜索来源列表 */
  const streamingSources = ref<Source[]>([])

  /** 流式生成是否正在进行中 */
  const isStreaming = ref(false)

  /** 流式生成是否已完成 */
  const isDone = ref(false)

  /** 当前问题的ID（生成完成后赋值） */
  const currentQuestionId = ref('')

  /** 当前答案的ID（生成完成后赋值） */
  const currentAnswerId = ref('')

  // ========== 操作方法 ==========

  /** 开始新一轮流式生成，重置所有状态 */
  function startStreaming() {
    streamingContent.value = ''
    streamingCategory.value = ''
    streamingType.value = 'insight'
    streamingFlowchart.value = ''
    streamingSteps.value = []
    streamingSources.value = []
    isStreaming.value = true
    isDone.value = false
    currentQuestionId.value = ''
    currentAnswerId.value = ''
  }

  /** 追加正文段落 */
  function appendContent(chunk: string) {
    streamingContent.value += chunk + '\n\n'
  }

  /** 设置分类 */
  function setCategory(category: string) {
    streamingCategory.value = category
  }

  /** 设置答案类型 */
  function setType(type: 'action' | 'insight') {
    streamingType.value = type
  }

  /** 设置流程图 */
  function setFlowchart(mermaid: string) {
    streamingFlowchart.value = mermaid
  }

  /** 设置步骤 */
  function setSteps(steps: SolutionStep[]) {
    streamingSteps.value = steps
  }

  /** 设置来源 */
  function setSources(sources: Source[]) {
    streamingSources.value = sources
  }

  /** 标记完成 */
  function finishStreaming(questionId: string, answerId: string) {
    currentQuestionId.value = questionId
    currentAnswerId.value = answerId
    isDone.value = true
    isStreaming.value = false
  }

  /** 重置整个store */
  function reset() {
    streamingContent.value = ''
    streamingCategory.value = ''
    streamingType.value = 'insight'
    streamingFlowchart.value = ''
    streamingSteps.value = []
    streamingSources.value = []
    isStreaming.value = false
    isDone.value = false
    currentQuestionId.value = ''
    currentAnswerId.value = ''
  }

  return {
    streamingContent,
    streamingCategory,
    streamingType,
    streamingFlowchart,
    streamingSteps,
    streamingSources,
    isStreaming,
    isDone,
    currentQuestionId,
    currentAnswerId,
    startStreaming,
    appendContent,
    setCategory,
    setType,
    setFlowchart,
    setSteps,
    setSources,
    finishStreaming,
    reset,
  }
})
