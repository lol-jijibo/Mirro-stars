<!--
  分享答案页 — 只读版答案展示
  业务角色：通过 /share/:answerId 链接访问，展示AI生成的完整解答方案。
  与 QuestionView 不同，此页面：
  1. 通过 answer_id 加载数据（而非 question_id）
  2. 只读展示，不含反馈、追问等交互功能
  3. 适合分享到社交媒体或转发给朋友
-->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { fetchAnswerByAnswerId } from '@/api/client'
import type { AnswerWithQuestion } from '@/types'
import StreamingAnswer from '@/components/StreamingAnswer.vue'
import ActionSummaryPanel from '@/components/ActionSummaryPanel.vue'
import FlowchartViewer from '@/components/FlowchartViewer.vue'
import SolutionSteps from '@/components/SolutionSteps.vue'
import SourceList from '@/components/SourceList.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import ReadingProgress from '@/components/ReadingProgress.vue'

const route = useRoute()

/** 答案+问题组合数据 */
const data = ref<AnswerWithQuestion | null>(null)
/** 是否正在加载 */
const isLoading = ref(true)
/** 加载错误信息 */
const loadError = ref('')

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

/** 分享当前页面（调起系统分享） */
function handleShare() {
  const url = window.location.href
  const title = data.value?.question?.content || 'Mirro AI 解答'

  if (navigator.share) {
    navigator.share({
      title: 'Mirro AI 解答',
      text: title.slice(0, 100),
      url,
    }).catch(() => { /* 用户取消分享 */ })
  } else {
    // 桌面端降级：复制链接
    navigator.clipboard.writeText(url).then(() => {
      // 简单的视觉反馈
      const btn = document.getElementById('share-btn')
      if (btn) {
        const original = btn.textContent
        btn.textContent = '✅ 链接已复制'
        setTimeout(() => { btn.textContent = original }, 2000)
      }
    }).catch(() => { /* 复制失败静默 */ })
  }
}

onMounted(async () => {
  try {
    data.value = await fetchAnswerByAnswerId(route.params.answerId as string)
  } catch {
    loadError.value = '答案不存在或已被删除'
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- 阅读进度条 + 回到顶部 -->
    <ReadingProgress />
    <!-- 加载中 — 骨架屏 -->
    <SkeletonLoader v-if="isLoading" type="answer" />

    <!-- 加载出错 -->
    <div v-else-if="loadError" class="text-center py-12">
      <p class="text-4xl mb-3">🔗</p>
      <p class="text-red-500 dark:text-red-400">{{ loadError }}</p>
      <p class="text-sm text-slate-400 dark:text-slate-500 mt-2">分享链接可能已失效</p>
    </div>

    <!-- 答案内容区 -->
    <template v-else-if="data">
      <!-- 顶部横幅 — 分享标识 -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <span class="text-lg">🪞</span>
          <span class="font-semibold text-slate-700 dark:text-slate-300">Mirro</span>
          <span>· AI 问题解决引擎</span>
        </div>
        <button
          id="share-btn"
          class="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 dark:bg-indigo-500 text-white text-sm font-medium rounded-lg
                 hover:bg-indigo-700 dark:hover:bg-indigo-600 active:scale-95 transition-all"
          @click="handleShare"
        >
          📤 分享
        </button>
      </div>

      <!-- 问题卡片 — 居中展示提问内容 -->
      <div class="relative bg-white dark:bg-slate-800 rounded-2xl border border-amber-100/40 dark:border-amber-800/20 pt-4 pb-8 px-8 text-center"
        style="box-shadow: 0 8px 32px rgba(245,158,11,0.14), 0 2px 8px rgba(0,0,0,0.08), 0 0 0 1px rgba(245,158,11,0.04);"
      >
        <!-- 装饰线 -->
        <div class="w-16 h-1 bg-amber-400 rounded-full mx-auto mb-4 opacity-50" />
        <!-- 问题内容 -->
        <p class="text-3xl font-semibold text-amber-900 dark:text-amber-200 leading-relaxed tracking-tight">
          {{ data.question.content }}
        </p>
        <!-- 底部信息 -->
        <div class="mt-3 flex items-center justify-center gap-3">
          <span class="text-xs text-amber-500 dark:text-amber-400">
            {{ formatTime(data.question.created_at) }}
          </span>
          <span
            v-if="data.question.category"
            class="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300"
          >
            {{ data.question.category }}
          </span>
        </div>
      </div>

      <!-- 顶部行动摘要 -->
      <ActionSummaryPanel
        v-if="data.answer.action_summary"
        :summary="data.answer.action_summary"
      />

      <!-- AI答案正文 — Markdown渲染 -->
      <section>
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3 flex items-center gap-3">
          <template v-if="data.answer.type === 'insight'">🧠 深度分析</template>
          <template v-else>🧠 AI 分析解答</template>
        </h2>
        <StreamingAnswer
          :content="data.answer.content"
          :is-done="true"
        />
      </section>

      <!-- 答案类型提示 — insight 类型强调深度阅读 -->
      <div
        v-if="data.answer.type === 'insight'"
        class="flex items-center gap-2 px-4 py-3 bg-indigo-50 dark:bg-indigo-950 border border-indigo-100 dark:border-indigo-800 rounded-lg text-sm text-indigo-700 dark:text-indigo-300"
      >
        <span>💡</span> 这是一个深度分析型问题，AI 从多角度进行了剖析，请仔细阅读正文获取完整见解。
      </div>

      <!-- 解决方案流程图 -->
      <section v-if="data.answer.flowchart_mermaid">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">📊 解决方案流程图</h2>
        <FlowchartViewer :mermaid-text="data.answer.flowchart_mermaid" />
      </section>

      <!-- 分步执行计划 -->
      <section v-if="data.answer.steps.length > 0">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">📋 分步执行计划</h2>
        <SolutionSteps :steps="data.answer.steps" readonly />
      </section>

      <!-- 参考案例与来源 -->
      <section v-if="data.answer.sources.length > 0">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">🌐 参考案例与来源</h2>
        <SourceList :sources="data.answer.sources" />
      </section>

      <!-- 底部 — Mirro 品牌 + 提问入口 -->
      <div class="border-t border-slate-200 dark:border-slate-700 pt-6 text-center">
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-3">
          由 <span class="font-semibold text-slate-700 dark:text-slate-300">🪞 Mirro AI</span> 生成
        </p>
        <a
          href="/"
          class="inline-flex items-center gap-1.5 px-5 py-2.5 bg-indigo-600 dark:bg-indigo-500 text-white text-sm font-medium rounded-lg
                 hover:bg-indigo-700 dark:hover:bg-indigo-600 transition-all"
        >
          🚀 我也要提问
        </a>
      </div>
    </template>
  </div>
</template>
