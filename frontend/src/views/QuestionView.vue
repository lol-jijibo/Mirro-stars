<!--
  答案详情页 — 展示AI生成的完整解答方案
  业务角色：这是Mirro的核心展示页面，汇总AI答案的所有维度：
  正文(Markdown) + 流程图(Mermaid) + 分步计划 + 搜索来源。
  支持两种数据来源：
  1. SSE流式生成中 → 从Pinia store读取实时数据
  2. 直接访问URL → 从后端API加载持久化数据
-->
<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuestionStore } from '@/stores/question'
import { fetchQuestionDetail, fetchRelatedQuestions, streamQuestion } from '@/api/client'
import type { QuestionDetail, ActionSummary } from '@/types'
import QuestionInput from '@/components/QuestionInput.vue'
import StreamingAnswer from '@/components/StreamingAnswer.vue'
import ActionSummaryPanel from '@/components/ActionSummaryPanel.vue'
import FlowchartViewer from '@/components/FlowchartViewer.vue'
import SolutionSteps from '@/components/SolutionSteps.vue'
import SourceList from '@/components/SourceList.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import ReadingProgress from '@/components/ReadingProgress.vue'
import AnswerToc from '@/components/AnswerToc.vue'

type FollowUpMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  status: 'streaming' | 'done' | 'error'
}

const route = useRoute()
const router = useRouter()
const store = useQuestionStore()

/** 从API加载的持久化数据（直接访问URL时使用） */
const questionDetail = ref<QuestionDetail | null>(null)
/** 是否正在加载 */
const isLoading = ref(false)
/** 加载错误信息 */
const loadError = ref('')

// ========== 追问状态 ==========
/** 追问输入内容 */
const followUpContent = ref('')
/** 是否正在提交追问 */
const isFollowingUp = ref(false)
/** 详情页内追问消息列表 */
const followUpMessages = ref<FollowUpMessage[]>([])
/** 当前追问的SSE连接引用 */
const activeFollowUpStream = ref<EventSource | null>(null)
/** 追问错误信息 */
const followUpError = ref('')

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
  return store.isDone
    && store.currentQuestionId === route.params.id
    && store.streamingContent.trim().length > 0
})

/** 获取问题分类（优先从stream store，其次从API数据） */
const questionCategory = computed(() => {
  if (isFromStream.value) return store.streamingCategory
  return questionDetail.value?.category || ''
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

/** 判断当前详情页是否已经拿到可展示的答案内容 */
const hasAnswerContent = computed(() => answerContent.value.trim().length > 0)

/** 判断当前详情页是否已经拿到答案相关数据 */
const hasAnswerData = computed(() => {
  return hasAnswerContent.value || !!questionDetail.value?.answer || isFromStream.value
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

/** 获取顶部行动摘要 */
const actionSummary = computed<ActionSummary | null>(() => {
  if (isFromStream.value) return store.streamingActionSummary
  return questionDetail.value?.answer?.action_summary || null
})

/** 加载持久化的问题详情 */
async function loadQuestionDetail() {
  isLoading.value = true
  loadError.value = ''
  try {
    questionDetail.value = await fetchQuestionDetail(route.params.id as string)
    console.info('[Mirro] 问题详情已加载', {
      questionId: route.params.id,
      hasAnswer: !!questionDetail.value?.answer,
      answerLength: questionDetail.value?.answer?.content?.length || 0,
    })
  } catch (err) {
    loadError.value = '加载失败，请刷新重试'
  } finally {
    isLoading.value = false
  }
}

/** 追问 */

/** 处理追问提交 — 在详情页内直接追加AI回答 */
function handleFollowUp(inputContent?: string) {
  const content = (inputContent ?? followUpContent.value).trim()
  if (!content || content.length < 5 || isFollowingUp.value) return

  followUpError.value = ''
  isFollowingUp.value = true
  followUpContent.value = ''

  followUpMessages.value.push({
    id: `user-${Date.now()}`,
    role: 'user',
    content,
    status: 'done',
  })

  const assistantMessage: FollowUpMessage = {
    id: `assistant-${Date.now()}`,
    role: 'assistant',
    content: '',
    status: 'streaming',
  }
  followUpMessages.value.push(assistantMessage)

  activeFollowUpStream.value = streamQuestion(
    content,
    (type, data) => {
      switch (type) {
        case 'content':
          assistantMessage.content += `${data}\n\n`
          break
        case 'error':
          try {
            const err = JSON.parse(data)
            followUpError.value = err.message || 'AI 解答失败，请稍后重试'
          } catch {
            followUpError.value = data || 'AI 解答失败，请稍后重试'
          }
          assistantMessage.status = 'error'
          if (!assistantMessage.content) assistantMessage.content = followUpError.value
          isFollowingUp.value = false
          activeFollowUpStream.value = null
          break
        case 'done':
          assistantMessage.status = 'done'
          isFollowingUp.value = false
          activeFollowUpStream.value = null
          break
      }
    },
    (error) => {
      followUpError.value = `生成失败: ${error}`
      assistantMessage.status = 'error'
      if (!assistantMessage.content) assistantMessage.content = followUpError.value
      isFollowingUp.value = false
      activeFollowUpStream.value = null
    },
    route.params.id as string
  )
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
  loadQuestionDetail().then(() => {
    if (isFromStream.value) {
      nextTick(() => loadRelatedQuestions())
    } else {
      loadRelatedQuestions()
    }
  })
})

onUnmounted(() => {
  if (activeFollowUpStream.value) {
    activeFollowUpStream.value.close()
    activeFollowUpStream.value = null
  }
})
</script>

<template>
  <div class="space-y-6 pb-20">
    <!-- 阅读进度条 + 回到顶部 -->
    <ReadingProgress />

    <!-- 答案目录导航(TOC) — 仅大屏显示 -->
    <AnswerToc
      :content="answerContent"
      :is-done="hasAnswerData"
    />
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
          <span
            v-if="questionCategory && questionCategory !== '分析中...'"
            class="text-xs px-2.5 py-0.5 rounded-full bg-amber-100/60 dark:bg-amber-800/40 text-amber-700 dark:text-amber-300 font-medium"
          >
            {{ questionCategory }}
          </span>
          <span class="text-xs text-amber-500 dark:text-amber-400">
            <template v-if="isFromStream">刚刚</template>
            <template v-else>{{ questionDetail?.created_at ? formatTime(questionDetail.created_at) : '' }}</template>
          </span>
        </div>
      </div>

      <!-- 导出区域 — 分享/导出时截取此区域内容 -->
      <div ref="exportAreaRef" class="space-y-6">
      <!-- 顶部行动摘要 — 先给用户下一步、周期和风险 -->
      <ActionSummaryPanel
        v-if="actionSummary"
        :summary="actionSummary"
      />

      <!-- AI答案正文 — Markdown流式渲染 -->
      <section v-if="hasAnswerContent">
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
          :is-done="hasAnswerData"
        />
      </section>

      <section
        v-else
        class="rounded-xl border border-amber-200/70 bg-amber-50 px-5 py-4 text-sm text-amber-800 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-200"
      >
        已加载到问题，但还没有拿到答案正文。请刷新一次页面，或回到历史页重新进入。
      </section>

      <!-- 答案类型提示 — insight 类型没有步骤，强调深度阅读 -->
      <div
        v-if="answerType === 'insight' && hasAnswerData"
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
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">📋 执行清单</h2>
        <SolutionSteps :steps="steps" :storage-key="route.params.id as string" />
      </section>

      <!-- 参考案例与来源 — 搜索引用 -->
      <section v-if="sources.length > 0">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">🌐 参考案例与来源</h2>
        <SourceList :sources="sources" />
      </section>

      </div>
      <!-- /导出区域 -->

      <!-- 追问消息区域 — 当前详情页内继续对话 -->
      <section v-if="hasAnswerData && followUpMessages.length > 0" class="border-t border-slate-200 dark:border-slate-700 pt-6">
        <div class="space-y-4">
          <div class="space-y-3">
            <div
              v-for="message in followUpMessages"
              :key="message.id"
              class="flex"
              :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
            >
              <div
                v-if="message.role === 'user'"
                class="max-w-[86%] rounded-2xl rounded-br-md bg-indigo-600 px-4 py-3 text-sm leading-relaxed text-white shadow-sm"
              >
                {{ message.content }}
              </div>
              <div v-else class="max-w-[92%]">
                <StreamingAnswer
                  :content="message.content"
                  :is-done="message.status !== 'streaming'"
                />
              </div>
            </div>
          </div>
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
      <div v-else-if="!isRelatedLoading && hasAnswerData" class="border-t border-slate-200 dark:border-slate-700 pt-6">
        <p class="text-sm text-slate-400 dark:text-slate-500 text-center">暂无相似问题推荐，多问几个问题后这里会更有趣 🎯</p>
      </div>

      <!-- 相关推荐加载中 -->
      <div v-else-if="isRelatedLoading" class="border-t border-slate-200 dark:border-slate-700 pt-6">
        <div class="space-y-2">
          <div v-for="i in 3" :key="i" class="h-12 bg-slate-100 dark:bg-slate-800 rounded-lg animate-pulse" />
        </div>
      </div>

      <!-- 空状态 — 无答案数据 -->
      <div v-if="!hasAnswerData && !isLoading" class="text-center py-12 text-slate-400 dark:text-slate-500">
        <p class="text-4xl mb-3">📭</p>
        <p>该问题暂无解答数据</p>
      </div>
    </template>

    <!-- 底部固定追问输入区 — 使用原本提问输入框样式 -->
    <div
      v-if="hasAnswerData"
      class="fixed left-0 right-0 bottom-0 z-40 pb-4 pt-3 pointer-events-none"
    >
      <div class="w-full max-w-4xl mx-auto px-4 pointer-events-auto">
        <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-2xl shadow-lg px-4 py-3 transition-all duration-200 focus-within:border-indigo-400 dark:focus-within:border-indigo-400 focus-within:shadow-xl">
          <QuestionInput
            :loading="isFollowingUp"
            placeholder="遇到什么问题了嘛,Mirro随时待命!"
            submit-icon="↑"
            submit-text="求解"
            inline-submit
            hide-hint
            @submit="handleFollowUp"
          />
          <p v-if="followUpError" class="mt-3 text-sm text-red-500 dark:text-red-400">
            {{ followUpError }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
