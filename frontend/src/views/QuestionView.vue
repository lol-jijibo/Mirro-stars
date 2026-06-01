<!--
  答案详情页 — 展示AI生成的完整解答方案
  业务角色：这是Mirro的核心展示页面，汇总AI答案的所有维度：
  正文(Markdown) + 流程图(Mermaid) + 分步计划 + 搜索来源。
  支持两种数据来源：
  1. SSE流式生成中 → 从Pinia store读取实时数据
  2. 直接访问URL → 从后端API加载持久化数据
-->
<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuestionStore } from '@/stores/question'
import { fetchQuestionDetail, submitFeedback, fetchFeedback, fetchRelatedQuestions } from '@/api/client'
import type { QuestionDetail, FeedbackResponse } from '@/types'
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

// ========== 反馈状态 ==========
/** 已提交的反馈记录 */
const existingFeedback = ref<FeedbackResponse | null>(null)
/** 当前评分：1=好评, -1=差评, 0=未评分 */
const currentRating = ref(0)
/** 反馈文字评论 */
const feedbackComment = ref('')
/** 是否正在提交反馈 */
const isSubmittingFeedback = ref(false)
/** 反馈是否已提交 */
const feedbackSubmitted = ref(false)
/** 是否显示评论输入框 */
const showCommentInput = ref(false)

// ========== 追问状态 ==========
/** 追问输入内容 */
const followUpContent = ref('')
/** 是否正在提交追问（跳转中） */
const isFollowingUp = ref(false)

// ========== 分享状态 ==========
/** 分享链接是否已复制 */
const shareCopied = ref(false)

// ========== 导出状态 ==========
/** 是否正在导出 */
const isExporting = ref(false)
/** 导出内容区的ref，用于html2canvas截图 */
const exportAreaRef = ref<HTMLElement | null>(null)

// ========== 相关推荐状态 ==========
/** AI生成的相关推荐问题列表（纯文本，点击后跳转首页提交） */
const relatedQuestions = ref<string[]>([])
/** 相关推荐是否正在加载 */
const isRelatedLoading = ref(false)

/**
 * 判断当前是否在流式生成中
 * SSE流式数据走store，API持久化数据走questionDetail
 */
const isFromStream = computed(() => {
  return store.isDone && store.currentQuestionId === route.params.id
})

/** 获取问题内容（优先从stream store，其次从API数据） */
const questionContent = computed(() => {
  if (isFromStream.value) return store.streamingQuestion
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
    // 加载已有的反馈
    await loadExistingFeedback()
  } catch (err) {
    loadError.value = '加载失败，请刷新重试'
  } finally {
    isLoading.value = false
  }
}

/** 加载已提交的反馈记录 */
async function loadExistingFeedback() {
  try {
    const result = await fetchFeedback(route.params.id as string)
    if (result.feedbacks.length > 0) {
      existingFeedback.value = result.feedbacks[0]
      currentRating.value = result.feedbacks[0].rating
      feedbackComment.value = result.feedbacks[0].comment || ''
      feedbackSubmitted.value = true
    }
  } catch {
    // 加载反馈失败静默
  }
}

/** 提交评分反馈 */
async function handleRate(rating: number) {
  if (feedbackSubmitted.value) return
  currentRating.value = rating
  showCommentInput.value = true
}

/** 提交完整反馈（评分 + 可选文字） */
async function handleSubmitFeedback() {
  if (feedbackSubmitted.value || currentRating.value === 0) return

  isSubmittingFeedback.value = true
  try {
    const answerId = questionDetail.value?.answer?.id || store.currentAnswerId
    if (!answerId) return

    await submitFeedback(route.params.id as string, {
      answer_id: answerId,
      rating: currentRating.value,
      comment: feedbackComment.value.trim() || undefined,
    })
    feedbackSubmitted.value = true
    showCommentInput.value = false
  } catch {
    // 提交失败静默
  } finally {
    isSubmittingFeedback.value = false
  }
}

/** 取消反馈评论 */
function cancelComment() {
  showCommentInput.value = false
  feedbackComment.value = ''
  if (!feedbackSubmitted.value) {
    currentRating.value = 0
  }
}

/** 处理追问提交 — 跳转到首页并携带 conversation_id */
function handleFollowUp() {
  const content = followUpContent.value.trim()
  if (!content || content.length < 5) return

  isFollowingUp.value = true
  // 用当前问题的ID作为conversation_id，跳转到首页提问
  // 首页的handleSubmit会从query params中读取并传给后端
  router.push({
    path: '/',
    query: {
      conversation_id: route.params.id as string,
      follow_up: content,
    },
  })
}

// ========== 分享功能 ==========

/** 计算当前答案的分享链接 */
const shareUrl = computed(() => {
  const answerId = store.currentAnswerId || questionDetail.value?.answer?.id
  if (!answerId) return ''
  return `${window.location.origin}/share/${answerId}`
})

/** 处理分享 — 移动端调起系统分享，桌面端复制链接 */
async function handleShare() {
  const url = shareUrl.value
  if (!url) return

  if (navigator.share) {
    try {
      await navigator.share({
        title: 'Mirro AI 解答',
        text: questionContent.value.slice(0, 100),
        url,
      })
    } catch {
      // 用户取消分享，静默处理
    }
  } else {
    // 桌面端降级：复制链接到剪贴板
    try {
      await navigator.clipboard.writeText(url)
      shareCopied.value = true
      setTimeout(() => { shareCopied.value = false }, 2500)
    } catch {
      // 复制失败静默
    }
  }
}

// ========== 导出功能 ==========

/** 导出为PNG图片 */
async function exportPNG() {
  if (isExporting.value || !exportAreaRef.value) return
  isExporting.value = true
  try {
    const html2canvas = (await import('html2canvas')).default
    const canvas = await html2canvas(exportAreaRef.value, {
      backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--color-slate-800').trim() || '#ffffff',
      scale: 2,
      useCORS: true,
      logging: false,
    })
    const link = document.createElement('a')
    link.download = `Mirro-解答-${Date.now()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
  } catch (err) {
    console.error('导出PNG失败:', err)
  } finally {
    isExporting.value = false
  }
}

/** 导出为PDF文件 */
async function exportPDF() {
  if (isExporting.value || !exportAreaRef.value) return
  isExporting.value = true
  try {
    const html2canvas = (await import('html2canvas')).default
    const { jsPDF } = await import('jspdf')

    const canvas = await html2canvas(exportAreaRef.value, {
      backgroundColor: '#ffffff',
      scale: 2,
      useCORS: true,
      logging: false,
    })

    const imgData = canvas.toDataURL('image/png')
    const imgWidth = 210 // A4 width in mm
    const imgHeight = (canvas.height * imgWidth) / canvas.width

    const pdf = new jsPDF('p', 'mm', 'a4')
    pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight)

    // 如果内容超过一页，自动分页
    const pageHeight = 297 // A4 height in mm
    let heightLeft = imgHeight
    let position = 0

    while (heightLeft > pageHeight) {
      position = -(pageHeight)
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= pageHeight
    }

    pdf.save(`Mirro-解答-${Date.now()}.pdf`)
  } catch (err) {
    console.error('导出PDF失败:', err)
  } finally {
    isExporting.value = false
  }
}

// ========== 相关推荐 ==========

/** 加载相关推荐：优先从答案数据读取，无缓存时才调API */
async function loadRelatedQuestions() {
  // 优先从 stream store 读取（SSE刚生成完，零延迟零token）
  if (store.streamingRelatedQuestions.length > 0) {
    relatedQuestions.value = store.streamingRelatedQuestions
    return
  }

  // 其次从 API 返回的答案数据读取（DB已有缓存）
  if (questionDetail.value?.answer?.related_questions?.length) {
    relatedQuestions.value = questionDetail.value.answer.related_questions
    return
  }

  // 最后降级：旧数据无缓存，调API实时生成（仅一次，之后会缓存到DB）
  const questionId = route.params.id as string
  if (!questionId) return

  isRelatedLoading.value = true
  try {
    const result = await fetchRelatedQuestions(questionId)
    relatedQuestions.value = result.related_questions
  } catch (err) {
    console.error('[Mirro] 加载相关推荐失败:', err)
    relatedQuestions.value = []
  } finally {
    isRelatedLoading.value = false
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
    loadQuestionDetail().then(() => loadRelatedQuestions())
  } else {
    // 从SSE流式过来的，也尝试加载已有反馈
    loadExistingFeedback()
    // 等待一小段时间让store数据稳定后加载推荐
    nextTick(() => loadRelatedQuestions())
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- 加载中 — 骨架屏 -->
    <SkeletonLoader v-if="isLoading" type="answer" />

    <!-- 加载出错 -->
    <div v-else-if="loadError" class="text-center py-12 text-red-500">
      {{ loadError }}
    </div>

    <!-- 答案内容区 -->
    <template v-else>
      <!-- 问题卡片 — 居中展示提问内容，大字号 + 层次感阴影 -->
      <div class="relative bg-white dark:bg-slate-800 rounded-2xl border border-amber-100/40 dark:border-amber-800/20 pt-4 pb-8 px-8 text-center"
        style="box-shadow: 0 8px 32px rgba(245,158,11,0.14), 0 2px 8px rgba(0,0,0,0.08), 0 0 0 1px rgba(245,158,11,0.04);"
      >
        <!-- 返回按钮 — 左上角 -->
        <button
          class="absolute top-3 left-4 flex items-center gap-1 text-sm text-slate-400 dark:text-slate-500 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
          @click="router.push('/')"
        >
          ← 返回首页
        </button>
        <!-- 操作按钮组 — 右上角：分享 + 导出 -->
        <div class="absolute top-3 right-4 flex items-center gap-1.5">
          <!-- 分享按钮 -->
          <button
            class="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 active:scale-95"
            :class="shareCopied
              ? 'bg-green-50 dark:bg-green-950 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800'
              : 'bg-white dark:bg-slate-700 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-600 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400'"
            :disabled="!shareUrl"
            @click="handleShare"
          >
            {{ shareCopied ? '✅ 已复制' : '📤 分享' }}
          </button>
          <!-- 导出PNG -->
          <button
            class="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-white dark:bg-slate-700 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-600 hover:border-emerald-300 dark:hover:border-emerald-600 hover:text-emerald-600 dark:hover:text-emerald-400 transition-all duration-150 active:scale-95"
            :disabled="isExporting"
            @click="exportPNG"
          >
            {{ isExporting ? '⏳' : '🖼️' }} PNG
          </button>
          <!-- 导出PDF -->
          <button
            class="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-white dark:bg-slate-700 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-600 hover:border-rose-300 dark:hover:border-rose-600 hover:text-rose-600 dark:hover:text-rose-400 transition-all duration-150 active:scale-95"
            :disabled="isExporting"
            @click="exportPDF"
          >
            {{ isExporting ? '⏳' : '📄' }} PDF
          </button>
        </div>
        <!-- 装饰线 -->
        <div class="w-16 h-1 bg-amber-400 rounded-full mx-auto mb-4 opacity-50" />
        <!-- 问题内容 — 居中大字 -->
        <p class="text-3xl font-semibold text-amber-900 dark:text-amber-200 leading-relaxed tracking-tight">
          {{ questionContent }}
        </p>
        <!-- 底部信息 -->
        <div class="mt-3 flex items-center justify-center gap-2">
          <span class="text-xs text-amber-500 dark:text-amber-400">
            <template v-if="isFromStream">刚刚</template>
            <template v-else>{{ questionDetail?.created_at ? formatTime(questionDetail.created_at) : '' }}</template>
          </span>
        </div>
      </div>

      <!-- 导出区域 — 分享/导出时截取此区域内容 -->
      <div ref="exportAreaRef" class="space-y-6">
      <!-- AI答案正文 — Markdown流式渲染 -->
      <section>
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3 flex items-center gap-3">
          <template v-if="answerType === 'insight'">🧠 深度分析</template>
          <template v-else>🧠 AI 分析解答</template>
          <!-- 生成耗时 — 仅流式完成后显示 -->
          <span
            v-if="store.streamingElapsed > 0"
            class="text-xs font-normal text-slate-400 dark:text-slate-500"
          >⏱️ 生成耗时 {{ store.streamingElapsed.toFixed(1) }}s</span>
        </h2>
        <StreamingAnswer
          :content="answerContent"
          :is-done="store.isDone || !!questionDetail?.answer"
        />
      </section>

      <!-- 答案类型提示 — insight 类型没有步骤，强调深度阅读 -->
      <div
        v-if="answerType === 'insight' && (store.isDone || questionDetail?.answer)"
        class="flex items-center gap-2 px-4 py-3 bg-indigo-50 dark:bg-indigo-950 border border-indigo-100 dark:border-indigo-800 rounded-lg text-sm text-indigo-700 dark:text-indigo-300"
      >
        <span>💡</span> 这是一个深度分析型问题，AI 从多角度进行了剖析，请仔细阅读正文获取完整见解。
      </div>

      <!-- 解决方案流程图 — Mermaid可视化（仅action类型） -->
      <section v-if="flowchartContent">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">📊 解决方案流程图</h2>
        <FlowchartViewer :mermaid-text="flowchartContent" />
      </section>

      <!-- 分步执行计划 — 时间轴卡片（仅action类型） -->
      <section v-if="steps.length > 0">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">📋 分步执行计划</h2>
        <SolutionSteps :steps="steps" />
      </section>

      <!-- 参考案例与来源 — 搜索引用 -->
      <section v-if="sources.length > 0">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">🌐 参考案例与来源</h2>
        <SourceList :sources="sources" />
      </section>

      </div>
      <!-- /导出区域 -->

      <!-- 答案反馈 — 👍👎 评分 -->
      <section v-if="(store.isDone || questionDetail?.answer)" class="border-t border-slate-200 dark:border-slate-700 pt-6">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">💬 这个答案对你有帮助吗？</h2>

        <!-- 已提交反馈提示 -->
        <div v-if="feedbackSubmitted" class="flex items-center gap-2 px-4 py-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg text-sm text-green-700 dark:text-green-300">
          <span>✅</span> 感谢你的反馈！
          <span v-if="currentRating === 1">很高兴能帮到你 👍</span>
          <span v-else-if="currentRating === -1">我们会继续改进 👎</span>
        </div>

        <!-- 评分按钮 -->
        <div v-else class="flex items-center gap-3">
          <button
            class="flex items-center gap-2 px-5 py-2.5 rounded-lg border text-sm font-medium transition-all duration-150 active:scale-95"
            :class="currentRating === 1
              ? 'bg-green-50 dark:bg-green-950 border-green-300 dark:border-green-700 text-green-700 dark:text-green-300'
              : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-green-300 dark:hover:border-green-700 hover:text-green-600 dark:hover:text-green-400'"
            @click="handleRate(1)"
          >
            👍 有帮助
          </button>
          <button
            class="flex items-center gap-2 px-5 py-2.5 rounded-lg border text-sm font-medium transition-all duration-150 active:scale-95"
            :class="currentRating === -1
              ? 'bg-red-50 dark:bg-red-950 border-red-300 dark:border-red-700 text-red-700 dark:text-red-300'
              : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-red-300 dark:hover:border-red-700 hover:text-red-600 dark:hover:text-red-400'"
            @click="handleRate(-1)"
          >
            👎 不够好
          </button>
        </div>

        <!-- 可选文字评论 -->
        <div v-if="showCommentInput && !feedbackSubmitted" class="mt-3 space-y-2">
          <textarea
            v-model="feedbackComment"
            placeholder="可选：告诉我们哪里好或哪里需要改进…"
            rows="2"
            maxlength="500"
            class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg
                   text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500
                   focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 resize-none"
          />
          <div class="flex items-center gap-2">
            <button
              class="px-4 py-1.5 text-sm font-medium bg-indigo-600 dark:bg-indigo-500 text-white rounded-lg
                     hover:bg-indigo-700 dark:hover:bg-indigo-600 active:scale-95 transition-all"
              :disabled="isSubmittingFeedback"
              @click="handleSubmitFeedback"
            >
              {{ isSubmittingFeedback ? '提交中…' : '提交反馈' }}
            </button>
            <button
              class="px-4 py-1.5 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
              @click="cancelComment"
            >
              取消
            </button>
          </div>
        </div>
      </section>

      <!-- 追问区域 — 多轮对话 -->
      <section v-if="(store.isDone || questionDetail?.answer)" class="border-t border-slate-200 dark:border-slate-700 pt-6">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">💬 继续追问</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-3">
          对答案还有疑问？提出追问，AI 会结合之前的对话上下文给出更深入的回答。
        </p>
        <div class="flex gap-2">
          <input
            v-model="followUpContent"
            type="text"
            placeholder="输入你的追问…（至少5个字）"
            class="flex-1 px-4 py-2.5 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg
                   text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500
                   focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 transition-all"
            @keydown.enter="handleFollowUp"
          />
          <button
            class="px-5 py-2.5 bg-indigo-600 dark:bg-indigo-500 text-white text-sm font-medium rounded-lg
                   hover:bg-indigo-700 dark:hover:bg-indigo-600 active:scale-95
                   disabled:bg-slate-300 dark:disabled:bg-slate-700 disabled:cursor-not-allowed
                   transition-all duration-150"
            :disabled="followUpContent.trim().length < 5 || isFollowingUp"
            @click="handleFollowUp"
          >
            {{ isFollowingUp ? '跳转中…' : '🔍 追问' }}
          </button>
        </div>
      </section>

      <!-- 相关推荐 — 同类问题 -->
      <section v-if="relatedQuestions.length > 0" class="border-t border-slate-200 dark:border-slate-700 pt-6">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">🔗 相关推荐</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-3">
          AI 根据当前话题生成的深度追问建议，点击即可探索
        </p>
        <div class="space-y-2">
          <div
            v-for="(q, idx) in relatedQuestions"
            :key="idx"
            class="flex items-center gap-3 px-4 py-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700
                   hover:border-indigo-300 dark:hover:border-indigo-600 cursor-pointer transition-all duration-150 group"
            @click="router.push({ path: '/', query: { follow_up: q } })"
          >
            <span class="text-sm text-slate-300 dark:text-slate-600 group-hover:text-indigo-400 dark:group-hover:text-indigo-500 transition-colors">
              💬
            </span>
            <span class="flex-1 text-sm text-slate-700 dark:text-slate-300 group-hover:text-indigo-700 dark:group-hover:text-indigo-300 transition-colors">
              {{ q }}
            </span>
            <span class="text-xs text-indigo-400 dark:text-indigo-500 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
              问问 →
            </span>
          </div>
        </div>
      </section>

      <!-- 相关推荐 — 无结果 -->
      <div v-else-if="!isRelatedLoading && (store.isDone || questionDetail?.answer)" class="border-t border-slate-200 dark:border-slate-700 pt-6">
        <p class="text-sm text-slate-400 dark:text-slate-500 text-center">暂无相似问题推荐，多问几个问题后这里会更有趣 🎯</p>
      </div>

      <!-- 相关推荐加载中 -->
      <div v-else-if="isRelatedLoading" class="border-t border-slate-200 dark:border-slate-700 pt-6">
        <div class="space-y-2">
          <div v-for="i in 3" :key="i" class="h-12 bg-slate-100 dark:bg-slate-800 rounded-lg animate-pulse" />
        </div>
      </div>

      <!-- 空状态 — 无答案数据 -->
      <div v-if="!isFromStream && !questionDetail?.answer && !isLoading" class="text-center py-12 text-slate-400 dark:text-slate-500">
        <p class="text-4xl mb-3">📭</p>
        <p>该问题暂无解答数据</p>
      </div>
    </template>
  </div>
</template>
