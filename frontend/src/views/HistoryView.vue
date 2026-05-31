<!--
  问题历史列表页 — 查看所有提问记录
  业务角色：用户在此浏览、回顾、删除历史提问。
  支持分页加载，按时间倒序排列，点击可进入详情页。
-->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchQuestions, deleteQuestion } from '@/api/client'
import type { QuestionResponse } from '@/types'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const router = useRouter()

/** 历史问题列表 */
const questions = ref<QuestionResponse[]>([])
/** 问题总数 */
const total = ref(0)
/** 当前页码 */
const page = ref(1)
/** 每页条数 */
const pageSize = 20
/** 是否加载中 */
const isLoading = ref(false)
/** 是否还有更多数据 */
const hasMore = ref(false)

/**
 * 加载问题历史列表
 * 业务场景：首次进入页面或翻页时加载问题记录。
 */
async function loadQuestions() {
  isLoading.value = true
  try {
    const data = await fetchQuestions(page.value, pageSize)
    if (page.value === 1) {
      questions.value = data.items
    } else {
      questions.value.push(...data.items)
    }
    total.value = data.total
    hasMore.value = questions.value.length < data.total
  } catch {
    // 加载失败静默
  } finally {
    isLoading.value = false
  }
}

/**
 * 删除问题记录
 * 业务场景：用户不想保留某条提问记录时删除。
 */
async function handleDelete(id: string) {
  try {
    await deleteQuestion(id)
    questions.value = questions.value.filter(q => q.id !== id)
    total.value--
  } catch {
    // 删除失败静默
  }
}

/** 加载更多 */
function loadMore() {
  page.value++
  loadQuestions()
}

/** 跳转到答案详情页 */
function goToQuestion(id: string) {
  router.push(`/question/${id}`)
}

/** 格式化时间为可读格式 */
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

/** 卡片渐变色系 — 6种不同配色轮换 */
const cardThemes = [
  { gradient: 'bg-gradient-to-br from-indigo-50 via-white to-violet-50 border border-indigo-100/60', glow: 'bg-indigo-200/20', accent: 'bg-indigo-400', text: 'text-indigo-900 group-hover:text-indigo-700', meta: 'text-indigo-400', arrow: 'bg-indigo-500', shadow: '0 2px 12px rgba(99,102,241,0.10), 0 1px 3px rgba(0,0,0,0.04)', hoverShadow: '0 12px 40px rgba(99,102,241,0.18), 0 4px 12px rgba(0,0,0,0.08)' },
  { gradient: 'bg-gradient-to-br from-sky-50 via-white to-cyan-50 border border-sky-100/60', glow: 'bg-sky-200/20', accent: 'bg-sky-400', text: 'text-sky-900 group-hover:text-sky-700', meta: 'text-sky-400', arrow: 'bg-sky-500', shadow: '0 2px 12px rgba(14,165,233,0.10), 0 1px 3px rgba(0,0,0,0.04)', hoverShadow: '0 12px 40px rgba(14,165,233,0.18), 0 4px 12px rgba(0,0,0,0.08)' },
  { gradient: 'bg-gradient-to-br from-emerald-50 via-white to-teal-50 border border-emerald-100/60', glow: 'bg-emerald-200/20', accent: 'bg-emerald-400', text: 'text-emerald-900 group-hover:text-emerald-700', meta: 'text-emerald-400', arrow: 'bg-emerald-500', shadow: '0 2px 12px rgba(16,185,129,0.10), 0 1px 3px rgba(0,0,0,0.04)', hoverShadow: '0 12px 40px rgba(16,185,129,0.18), 0 4px 12px rgba(0,0,0,0.08)' },
  { gradient: 'bg-gradient-to-br from-amber-50 via-white to-orange-50 border border-amber-100/60', glow: 'bg-amber-200/20', accent: 'bg-amber-400', text: 'text-amber-900 group-hover:text-amber-700', meta: 'text-amber-400', arrow: 'bg-amber-500', shadow: '0 2px 12px rgba(245,158,11,0.10), 0 1px 3px rgba(0,0,0,0.04)', hoverShadow: '0 12px 40px rgba(245,158,11,0.18), 0 4px 12px rgba(0,0,0,0.08)' },
  { gradient: 'bg-gradient-to-br from-rose-50 via-white to-pink-50 border border-rose-100/60', glow: 'bg-rose-200/20', accent: 'bg-rose-400', text: 'text-rose-900 group-hover:text-rose-700', meta: 'text-rose-400', arrow: 'bg-rose-500', shadow: '0 2px 12px rgba(244,63,94,0.10), 0 1px 3px rgba(0,0,0,0.04)', hoverShadow: '0 12px 40px rgba(244,63,94,0.18), 0 4px 12px rgba(0,0,0,0.08)' },
  { gradient: 'bg-gradient-to-br from-purple-50 via-white to-fuchsia-50 border border-purple-100/60', glow: 'bg-purple-200/20', accent: 'bg-purple-400', text: 'text-purple-900 group-hover:text-purple-700', meta: 'text-purple-400', arrow: 'bg-purple-500', shadow: '0 2px 12px rgba(168,85,247,0.10), 0 1px 3px rgba(0,0,0,0.04)', hoverShadow: '0 12px 40px rgba(168,85,247,0.18), 0 4px 12px rgba(0,0,0,0.08)' },
]

function gradientClass(idx: number) { return cardThemes[idx % cardThemes.length].gradient }
function glowClass(idx: number) { return cardThemes[idx % cardThemes.length].glow }
function accentClass(idx: number) { return cardThemes[idx % cardThemes.length].accent }
function textClass(idx: number) { return cardThemes[idx % cardThemes.length].text }
function metaClass(idx: number) { return cardThemes[idx % cardThemes.length].meta }
function arrowBgClass(idx: number) { return cardThemes[idx % cardThemes.length].arrow }
function cardShadow(idx: number) { return cardThemes[idx % cardThemes.length].shadow }
function cardHoverShadow(idx: number) { return cardThemes[idx % cardThemes.length].hoverShadow }

onMounted(() => {
  loadQuestions()
})
</script>

<template>
  <div class="space-y-4">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-slate-900">📋 问题历史</h1>
      <span class="text-sm text-slate-400">共 {{ total }} 条记录</span>
    </div>

    <!-- 骨架屏加载 -->
    <SkeletonLoader v-if="isLoading && questions.length === 0" type="list" />

    <!-- 空状态 -->
    <div v-else-if="questions.length === 0" class="text-center py-16">
      <p class="text-5xl mb-4">📭</p>
      <p class="text-slate-500 mb-4">还没有提问记录</p>
      <router-link
        to="/"
        class="inline-block px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
      >
        去提问
      </router-link>
    </div>

    <!-- 问题列表 — 居中渐变卡片风格 -->
    <div v-else class="space-y-3">
      <div
        v-for="(q, idx) in questions"
        :key="q.id"
        class="group relative rounded-2xl px-6 py-5 cursor-pointer transition-all duration-500 hover:-translate-y-1 hover:scale-[1.01]"
        :class="gradientClass(idx)"
        :style="{
          boxShadow: cardShadow(idx),
          animationDelay: `${idx * 60}ms`,
          animation: 'fadeInUp 0.4s ease-out both',
        }"
        @click="goToQuestion(q.id)"
        @mouseenter="(e) => { e.currentTarget.style.boxShadow = cardHoverShadow(idx) }"
        @mouseleave="(e) => { e.currentTarget.style.boxShadow = cardShadow(idx) }"
      >
        <!-- 背景光晕 -->
        <div
          class="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
          :class="glowClass(idx)"
        />

        <!-- 内容区 — 居中布局 -->
        <div class="relative flex flex-col items-center text-center gap-3">
          <!-- 顶部装饰线 -->
          <div
            class="w-10 h-0.5 rounded-full opacity-50"
            :class="accentClass(idx)"
          />

          <!-- 问题内容 — 居中大字展示 -->
          <p
            class="text-base font-semibold leading-relaxed line-clamp-2 transition-colors duration-300"
            :class="textClass(idx)"
          >
            {{ q.content }}
          </p>

          <!-- 底部时间 -->
          <span class="text-xs opacity-50" :class="metaClass(idx)">
            {{ formatTime(q.created_at) }}
          </span>

          <!-- hover 浮现的查看按钮 -->
          <div
            class="absolute -bottom-1 -right-1 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-1 group-hover:translate-y-0"
          >
            <div
              class="w-7 h-7 rounded-full flex items-center justify-center shadow-lg"
              :class="arrowBgClass(idx)"
            >
              <svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </div>

          <!-- 删除按钮 — hover 时显示在左上角 -->
          <button
            class="absolute -top-1 -left-1 opacity-0 group-hover:opacity-100 transition-all duration-300 text-slate-300 hover:text-red-500 p-1"
            title="删除此记录"
            @click.stop="handleDelete(q.id)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- 加载更多 -->
    <div v-if="hasMore" class="text-center pt-2">
      <button
        class="px-6 py-2 text-sm text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
        :disabled="isLoading"
        @click="loadMore"
      >
        {{ isLoading ? '加载中…' : '加载更多' }}
      </button>
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
