<!--
  答案详情页 — 展示AI生成的完整解答方案
  业务角色：这是Mirro的核心展示页面，汇总AI答案的所有维度：
  正文(Markdown) + 流程图(Mermaid) + 分步计划 + 搜索来源。
  支持两种数据来源：
  1. SSE流式生成中 → 从Pinia store读取实时数据
  2. 直接访问URL → 从后端API加载持久化数据
-->
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuestionStore } from '@/stores/question'
import { fetchQuestionDetail } from '@/api/client'
import type { QuestionDetail } from '@/types'
import StreamingAnswer from '@/components/StreamingAnswer.vue'
import FlowchartViewer from '@/components/FlowchartViewer.vue'
import SolutionSteps from '@/components/SolutionSteps.vue'
import SourceList from '@/components/SourceList.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const route = useRoute()
const router = useRouter()
const store = useQuestionStore()

/** 从API加载的持久化数据（直接访问URL时使用） */
const questionDetail = ref<QuestionDetail | null>(null)
/** 是否正在加载 */
const isLoading = ref(false)
/** 加载错误信息 */
const loadError = ref('')

/**
 * 判断当前是否在流式生成中
 * SSE流式数据走store，API持久化数据走questionDetail
 */
const isFromStream = computed(() => {
  return store.isDone && store.currentQuestionId === route.params.id
})

/** 获取问题内容（优先从stream，其次从API数据） */
const questionContent = computed(() => {
  if (isFromStream.value) return ''  // 流式场景下无原始问题存储
  return questionDetail.value?.content || ''
})

/** 获取答案类型 */
const answerType = computed(() => {
  if (isFromStream.value) return store.streamingType
  return questionDetail.value?.answer?.type || 'insight'
})

/** 获取答案正文 */
const answerContent = computed(() => {
  if (isFromStream.value) return store.streamingContent
  return questionDetail.value?.answer?.content || ''
})

/** 获取流程图 */
const flowchartContent = computed(() => {
  if (isFromStream.value) return store.streamingFlowchart
  return questionDetail.value?.answer?.flowchart_mermaid || ''
})

/** 获取分步计划 */
const steps = computed(() => {
  if (isFromStream.value) return store.streamingSteps
  return questionDetail.value?.answer?.steps || []
})

/** 获取搜索来源 */
const sources = computed(() => {
  if (isFromStream.value) return store.streamingSources
  return questionDetail.value?.answer?.sources || []
})

/** 加载持久化的问题详情 */
async function loadQuestionDetail() {
  isLoading.value = true
  loadError.value = ''
  try {
    questionDetail.value = await fetchQuestionDetail(route.params.id as string)
  } catch (err) {
    loadError.value = '加载失败，请刷新重试'
  } finally {
    isLoading.value = false
  }
}

/** 格式化时间为相对时间 */
function formatTime(isoString: string): string {
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHour = Math.floor(diffMs / 3600000)
  const diffDay = Math.floor(diffMs / 86400000)

  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  if (diffHour < 24) return `${diffHour} 小时前`
  if (diffDay < 7) return `${diffDay} 天前`
  return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
  // 如果不是刚从流式生成跳转过来的，就从API加载数据
  if (!isFromStream.value) {
    loadQuestionDetail()
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- 返回按钮 -->
    <button
      class="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 transition-colors"
      @click="router.push('/')"
    >
      ← 返回首页
    </button>

    <!-- 加载中 — 骨架屏 -->
    <SkeletonLoader v-if="isLoading" type="answer" />

    <!-- 加载出错 -->
    <div v-else-if="loadError" class="text-center py-12 text-red-500">
      {{ loadError }}
    </div>

    <!-- 答案内容区 -->
    <template v-else>
      <!-- 问题卡片 — 居中展示提问内容 -->
      <div class="bg-gradient-to-br from-indigo-50 via-white to-violet-50 rounded-2xl border border-indigo-100/60 p-6 text-center"
        style="box-shadow: 0 2px 16px rgba(99,102,241,0.10), 0 1px 3px rgba(0,0,0,0.04);"
      >
        <!-- 装饰线 -->
        <div class="w-12 h-0.5 bg-indigo-400 rounded-full mx-auto mb-3 opacity-60" />
        <!-- 问题内容 — 居中大字 -->
        <p class="text-xl font-semibold text-indigo-900 leading-relaxed">
          {{ questionContent }}
        </p>
        <!-- 底部信息 -->
        <div class="mt-3 flex items-center justify-center gap-2">
          <span class="text-xs text-indigo-400">
            {{ questionDetail?.created_at ? formatTime(questionDetail.created_at) : '' }}
          </span>
        </div>
      </div>

      <!-- AI答案正文 — Markdown流式渲染 -->
      <section>
        <h2 class="text-lg font-semibold text-slate-800 mb-3">
          <template v-if="answerType === 'insight'">🧠 深度分析</template>
          <template v-else>🧠 AI 分析解答</template>
        </h2>
        <StreamingAnswer
          :content="answerContent"
          :is-done="store.isDone || !!questionDetail?.answer"
        />
      </section>

      <!-- 答案类型提示 — insight 类型没有步骤，强调深度阅读 -->
      <div
        v-if="answerType === 'insight' && (store.isDone || questionDetail?.answer)"
        class="flex items-center gap-2 px-4 py-3 bg-indigo-50 border border-indigo-100 rounded-lg text-sm text-indigo-700"
      >
        <span>💡</span> 这是一个深度分析型问题，AI 从多角度进行了剖析，请仔细阅读正文获取完整见解。
      </div>

      <!-- 解决方案流程图 — Mermaid可视化（仅action类型） -->
      <section v-if="flowchartContent">
        <h2 class="text-lg font-semibold text-slate-800 mb-3">📊 解决方案流程图</h2>
        <FlowchartViewer :mermaid-text="flowchartContent" />
      </section>

      <!-- 分步执行计划 — 时间轴卡片（仅action类型） -->
      <section v-if="steps.length > 0">
        <h2 class="text-lg font-semibold text-slate-800 mb-3">📋 分步执行计划</h2>
        <SolutionSteps :steps="steps" />
      </section>

      <!-- 参考案例与来源 — 搜索引用 -->
      <section v-if="sources.length > 0">
        <h2 class="text-lg font-semibold text-slate-800 mb-3">🌐 参考案例与来源</h2>
        <SourceList :sources="sources" />
      </section>

      <!-- 空状态 — 无答案数据 -->
      <div v-if="!isFromStream && !questionDetail?.answer && !isLoading" class="text-center py-12 text-slate-400">
        <p class="text-4xl mb-3">📭</p>
        <p>该问题暂无解答数据</p>
      </div>
    </template>
  </div>
</template>
