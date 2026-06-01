<!--
  首页 — 用户进入应用的第一页面
  业务角色：提供问题输入入口 + 产品功能介绍，引导用户开始提问。
  这是整个Mirro产品流程的起点。
-->
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import QuestionInput from '@/components/QuestionInput.vue'
import { streamQuestion, fetchQuestions } from '@/api/client'
import { useQuestionStore } from '@/stores/question'
import type { SolutionStep, Source, QuestionResponse } from '@/types'

const router = useRouter()
const route = useRoute()
const store = useQuestionStore()

/** 是否正在生成答案（控制输入框禁用和导航栏状态） */
const isGenerating = ref(false)

/** 当前SSE连接引用（用于Esc取消） */
const activeStream = ref<EventSource | null>(null)

/** 错误消息 */
const errorMessage = ref('')

/** 最近用户提问列表 */
const recentQuestions = ref<QuestionResponse[]>([])
/** 最近提问是否加载中 */
const isQuestionsLoading = ref(false)

/**
 * 加载最近用户提问
 */
async function loadRecentQuestions() {
  isQuestionsLoading.value = true
  try {
    const data = await fetchQuestions(1, 6)
    recentQuestions.value = data.items
  } catch {
    // 加载失败静默
  } finally {
    isQuestionsLoading.value = false
  }
}

/**
 * 处理用户提交问题 — 启动SSE流式生成
 * 业务逻辑：提交问题→重置store→建立SSE连接→逐阶段处理事件→完成后跳转答案页
 */
function handleSubmit(question: string) {
  errorMessage.value = ''
  isGenerating.value = true

  // 检查URL中是否携带了conversation_id（从QuestionView追问跳转过来）
  const convId = (route.query.conversation_id as string) || ''

  // 初始化store状态，准备接收流式数据（同时保存原始提问文本）
  store.startStreaming(question, convId)

  // 建立SSE连接，逐阶段处理后端推送
  activeStream.value = streamQuestion(
    question,
    // onEvent — 每收到一个SSE事件时触发
    (type, data) => {
      switch (type) {
        case 'category':
          store.setCategory(data)
          break
        case 'type':
          store.setType(data as 'action' | 'insight')
          break
        case 'content':
          store.appendContent(data)
          break
        case 'flowchart':
          store.setFlowchart(data)
          break
        case 'steps':
          try {
            const steps: SolutionStep[] = JSON.parse(data)
            store.setSteps(steps)
          } catch { /* JSON解析失败静默 */ }
          break
        case 'related_questions':
          try {
            const questions: string[] = JSON.parse(data)
            store.setRelatedQuestions(questions)
          } catch { /* JSON解析失败静默 */ }
          break
        case 'sources':
          try {
            const sources: Source[] = JSON.parse(data)
            store.setSources(sources)
          } catch { /* JSON解析失败静默 */ }
          break
        case 'error':
          // 后端主动发送的错误事件
          try {
            const err = JSON.parse(data)
            errorMessage.value = `${err.message || '未知错误'}`
          } catch {
            errorMessage.value = data || '生成失败，请稍后重试'
          }
          isGenerating.value = false
          activeStream.value = null
          store.reset()
          break
        case 'done':
          try {
            const payload = JSON.parse(data)
            store.finishStreaming(payload.question_id, payload.answer_id)
            isGenerating.value = false
            activeStream.value = null
            // 生成完成 → 跳转到答案详情页
            router.push(`/question/${payload.question_id}`)
            // 浏览器通知：用户切到其他标签页时提醒
            sendBrowserNotification()
          } catch { /* JSON解析失败静默 */ }
          break
      }
    },
    // onError — 连接失败时触发（后端报错、网络错误等）
    (error) => {
      console.error('[Mirro] SSE连接失败:', error)
      errorMessage.value = `生成失败: ${error}`
      isGenerating.value = false
      activeStream.value = null
      store.reset()
    },
    convId || undefined  // 传入 conversation_id（空字符串不传）
  )
}

/**
 * 发送浏览器通知
 * 当SSE流完成时，如果用户切到了其他标签页，通过Notification API提醒。
 * 仅在页面不可见时发送，避免用户已在当前页面时产生干扰。
 */
function sendBrowserNotification() {
  // 只在页面不可见时发送通知（用户切到其他标签页）
  if (document.visibilityState !== 'hidden') return

  // 检查浏览器是否支持Notification API
  if (!('Notification' in window)) return

  if (Notification.permission === 'granted') {
    new Notification('Mirro AI', {
      body: '你的问题已解答完成，点击查看 →',
      icon: '/favicon.ico',
      tag: 'mirro-answer-done',
    })
  } else if (Notification.permission === 'default') {
    // 首次请求权限
    Notification.requestPermission().then((permission) => {
      if (permission === 'granted') {
        new Notification('Mirro AI', {
          body: '你的问题已解答完成，点击查看 →',
          icon: '/favicon.ico',
          tag: 'mirro-answer-done',
        })
      }
    })
  }
}

/** 取消当前生成 */
function cancelGeneration() {
  if (activeStream.value) {
    activeStream.value.close()
    activeStream.value = null
  }
  isGenerating.value = false
  store.reset()
}

/** 全局键盘快捷键 */
function onGlobalKeydown(e: KeyboardEvent) {
  // Esc → 取消生成
  if (e.key === 'Escape' && isGenerating.value) {
    e.preventDefault()
    cancelGeneration()
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

/** 卡片渐变色系 — 6种不同配色轮换，每张卡片都有独特的视觉识别度 */
const cardThemes = [
  { gradient: 'bg-gradient-to-br from-indigo-50 via-white to-violet-50 dark:from-indigo-950 dark:via-slate-900 dark:to-violet-950 border border-indigo-100/60 dark:border-indigo-800/30', glow: 'bg-indigo-200/20 dark:bg-indigo-500/10', accent: 'bg-indigo-400', text: 'text-indigo-900 dark:text-indigo-200 group-hover:text-indigo-700 dark:group-hover:text-indigo-300', meta: 'text-indigo-400 dark:text-indigo-500', arrow: 'bg-indigo-500', shadow: '0 2px 12px rgba(99,102,241,0.10), 0 1px 3px rgba(0,0,0,0.04)', hoverShadow: '0 12px 40px rgba(99,102,241,0.18), 0 4px 12px rgba(0,0,0,0.08)' },
  { gradient: 'bg-gradient-to-br from-sky-50 via-white to-cyan-50 dark:from-sky-950 dark:via-slate-900 dark:to-cyan-950 border border-sky-100/60 dark:border-sky-800/30', glow: 'bg-sky-200/20 dark:bg-sky-500/10', accent: 'bg-sky-400', text: 'text-sky-900 dark:text-sky-200 group-hover:text-sky-700 dark:group-hover:text-sky-300', meta: 'text-sky-400 dark:text-sky-500', arrow: 'bg-sky-500', shadow: '0 2px 12px rgba(14,165,233,0.10), 0 1px 3px rgba(0,0,0,0.04)', hoverShadow: '0 12px 40px rgba(14,165,233,0.18), 0 4px 12px rgba(0,0,0,0.08)' },
  { gradient: 'bg-gradient-to-br from-emerald-50 via-white to-teal-50 dark:from-emerald-950 dark:via-slate-900 dark:to-teal-950 border border-emerald-100/60 dark:border-emerald-800/30', glow: 'bg-emerald-200/20 dark:bg-emerald-500/10', accent: 'bg-emerald-400', text: 'text-emerald-900 dark:text-emerald-200 group-hover:text-emerald-700 dark:group-hover:text-emerald-300', meta: 'text-emerald-400 dark:text-emerald-500', arrow: 'bg-emerald-500', shadow: '0 2px 12px rgba(16,185,129,0.10), 0 1px 3px rgba(0,0,0,0.04)', hoverShadow: '0 12px 40px rgba(16,185,129,0.18), 0 4px 12px rgba(0,0,0,0.08)' },
  { gradient: 'bg-gradient-to-br from-amber-50 via-white to-orange-50 dark:from-amber-950 dark:via-slate-900 dark:to-orange-950 border border-amber-100/60 dark:border-amber-800/30', glow: 'bg-amber-200/20 dark:bg-amber-500/10', accent: 'bg-amber-400', text: 'text-amber-900 dark:text-amber-200 group-hover:text-amber-700 dark:group-hover:text-amber-300', meta: 'text-amber-400 dark:text-amber-500', arrow: 'bg-amber-500', shadow: '0 2px 12px rgba(245,158,11,0.10), 0 1px 3px rgba(0,0,0,0.04)', hoverShadow: '0 12px 40px rgba(245,158,11,0.18), 0 4px 12px rgba(0,0,0,0.08)' },
  { gradient: 'bg-gradient-to-br from-rose-50 via-white to-pink-50 dark:from-rose-950 dark:via-slate-900 dark:to-pink-950 border border-rose-100/60 dark:border-rose-800/30', glow: 'bg-rose-200/20 dark:bg-rose-500/10', accent: 'bg-rose-400', text: 'text-rose-900 dark:text-rose-200 group-hover:text-rose-700 dark:group-hover:text-rose-300', meta: 'text-rose-400 dark:text-rose-500', arrow: 'bg-rose-500', shadow: '0 2px 12px rgba(244,63,94,0.10), 0 1px 3px rgba(0,0,0,0.04)', hoverShadow: '0 12px 40px rgba(244,63,94,0.18), 0 4px 12px rgba(0,0,0,0.08)' },
  { gradient: 'bg-gradient-to-br from-purple-50 via-white to-fuchsia-50 dark:from-purple-950 dark:via-slate-900 dark:to-fuchsia-950 border border-purple-100/60 dark:border-purple-800/30', glow: 'bg-purple-200/20 dark:bg-purple-500/10', accent: 'bg-purple-400', text: 'text-purple-900 dark:text-purple-200 group-hover:text-purple-700 dark:group-hover:text-purple-300', meta: 'text-purple-400 dark:text-purple-500', arrow: 'bg-purple-500', shadow: '0 2px 12px rgba(168,85,247,0.10), 0 1px 3px rgba(0,0,0,0.04)', hoverShadow: '0 12px 40px rgba(168,85,247,0.18), 0 4px 12px rgba(0,0,0,0.08)' },
]

function gradientClass(idx: number) { return cardThemes[idx % cardThemes.length].gradient }
function glowClass(idx: number) { return cardThemes[idx % cardThemes.length].glow }
function accentClass(idx: number) { return cardThemes[idx % cardThemes.length].accent }
function textClass(idx: number) { return cardThemes[idx % cardThemes.length].text }
function metaClass(idx: number) { return cardThemes[idx % cardThemes.length].meta }
function arrowBgClass(idx: number) { return cardThemes[idx % cardThemes.length].arrow }
function cardShadow(idx: number) { return cardThemes[idx % cardThemes.length].shadow }
function cardHoverShadow(idx: number) { return cardThemes[idx % cardThemes.length].hoverShadow }

/** 跳转到问题详情页 */
function goToQuestion(id: string) {
  router.push(`/question/${id}`)
}

onMounted(() => {
  loadRecentQuestions()
  window.addEventListener('keydown', onGlobalKeydown)

  // 预先请求浏览器通知权限（用户首次访问时温和请求）
  if ('Notification' in window && Notification.permission === 'default') {
    // 延迟3秒请求，避免页面加载时立即弹出权限对话框
    setTimeout(() => {
      Notification.requestPermission()
    }, 3000)
  }

  // 处理从 QuestionView 追问跳转过来的场景
  // URL格式: /?conversation_id=xxx&follow_up=yyy
  const followUp = route.query.follow_up as string
  if (followUp && followUp.trim().length >= 5) {
    // 清除 URL 中的 follow_up 参数（保留 conversation_id），防止刷新时重复提交
    router.replace({ path: '/', query: { conversation_id: route.query.conversation_id } })
    handleSubmit(followUp.trim())
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
})
</script>

<template>
  <div class="flex flex-col items-center">
    <!-- 英雄区域 — 产品简介 -->
    <div class="text-center mb-10 mt-6">
      <h1 class="text-4xl font-bold text-slate-900 dark:text-slate-100 mb-3">
        <span class="text-5xl">🪞</span> Mirro
      </h1>
      <p class="text-lg text-slate-500 dark:text-slate-400 mb-1">AI 驱动的智能问题解决引擎</p>
      <p class="text-sm text-slate-400 dark:text-slate-500 max-w-md mx-auto">
        提出你的困惑 → AI 全网搜索案例 → 生成解决方案流程图 → 分步执行计划
      </p>
    </div>

    <!-- 提问输入区 — 核心交互 -->
    <div class="w-full max-w-2xl">
      <QuestionInput :loading="isGenerating" @submit="handleSubmit" />
    </div>

    <!-- 错误提示 -->
    <div v-if="errorMessage" class="mt-4 px-4 py-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm max-w-2xl w-full">
      {{ errorMessage }}
    </div>

    <!-- 最近用户提问 — 社区问题展示 -->
    <div class="w-full max-w-2xl mt-10">
      <!-- 标题 -->
      <div class="text-center mb-5">
        <h2 class="text-lg font-semibold text-slate-700 dark:text-slate-300">
          💬 大家最近在问
        </h2>
        <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">看看其他人都关心什么问题</p>
      </div>

      <!-- 加载骨架 — 匹配新卡片风格 -->
      <div v-if="isQuestionsLoading" class="space-y-4">
        <div
          v-for="i in 4"
          :key="i"
          class="bg-white rounded-2xl border border-slate-100 px-6 py-5 animate-pulse"
        >
          <div class="flex flex-col items-center gap-3">
            <div class="h-0.5 w-12 bg-slate-100 rounded-full" />
            <div class="h-5 w-3/4 bg-slate-50 rounded" />
            <div class="h-3 w-16 bg-slate-50 rounded" />
          </div>
        </div>
      </div>

      <!-- 问题卡片列表 — 居中展示用户提问，渐变卡片风格 -->
      <div v-else-if="recentQuestions.length > 0" class="space-y-4">
        <div
          v-for="(q, idx) in recentQuestions"
          :key="q.id"
          class="group relative rounded-2xl px-6 py-5 cursor-pointer transition-all duration-500 hover:-translate-y-1.5 hover:scale-[1.02]"
          :class="gradientClass(idx)"
          :style="{
            boxShadow: cardShadow(idx),
            animationDelay: `${idx * 100}ms`,
            animation: 'fadeInUp 0.5s ease-out both',
          }"
          @click="goToQuestion(q.id)"
          @mouseenter="(e) => { e.currentTarget.style.boxShadow = cardHoverShadow(idx) }"
          @mouseleave="(e) => { e.currentTarget.style.boxShadow = cardShadow(idx) }"
        >
          <!-- 背景光晕层 -->
          <div
            class="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
            :class="glowClass(idx)"
          />

          <!-- 内容区 — 居中布局 -->
          <div class="relative flex flex-col items-center text-center gap-3">
            <!-- 顶部装饰线 -->
            <div
              class="w-12 h-0.5 rounded-full opacity-60"
              :class="accentClass(idx)"
            />

            <!-- 问题内容 — 居中大字展示 -->
            <p
              class="text-lg font-semibold leading-relaxed line-clamp-2 transition-colors duration-300"
              :class="textClass(idx)"
            >
              {{ q.content }}
            </p>

            <!-- 底部信息：时间 -->
            <div class="flex items-center gap-1.5">
              <span class="text-xs opacity-60" :class="metaClass(idx)">
                {{ formatTime(q.created_at) }}
              </span>
            </div>

            <!-- 右下角查看提示 — hover 浮现 -->
            <div
              class="absolute -bottom-1 -right-1 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-1 group-hover:translate-y-0"
            >
              <div
                class="w-8 h-8 rounded-full flex items-center justify-center shadow-lg"
                :class="arrowBgClass(idx)"
              >
                <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="text-center py-10">
        <p class="text-4xl mb-3">📭</p>
        <p class="text-sm text-slate-400 dark:text-slate-500">还没有人提问，来做第一个提问者吧！</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
