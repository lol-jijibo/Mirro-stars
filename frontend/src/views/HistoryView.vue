<!--
  问题历史列表页 — 查看所有提问记录
  业务角色：用户在此浏览、回顾、删除历史提问。
  支持分页加载、关键词搜索、分类筛选，按时间倒序排列，点击可进入详情页。
-->
<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchQuestions, deleteQuestion } from '@/api/client'
import type { QuestionResponse } from '@/types'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const router = useRouter()

/** 7个预设分类（与后端AI分类体系一致） */
const CATEGORIES = [
  '全部',
  '职业发展',
  '情感关系',
  '个人成长',
  '理财规划',
  '健康生活',
  '社交技巧',
  '其他',
]

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
/** 搜索关键词 */
const searchQuery = ref('')
/** 分类筛选（"全部"表示不过滤） */
const selectedCategory = ref('全部')
/** 防抖定时器 */
let debounceTimer: ReturnType<typeof setTimeout> | null = null

/**
 * 加载问题历史列表
 * 业务场景：首次进入页面、翻页、搜索、筛选时加载问题记录。
 */
async function loadQuestions() {
  isLoading.value = true
  try {
    const search = searchQuery.value.trim()
    const category = selectedCategory.value === '全部' ? '' : selectedCategory.value
    const data = await fetchQuestions(page.value, pageSize, search, category)
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
 * 搜索输入防抖处理（300ms）
 * 业务场景：用户输入关键词后等待300ms再发起请求，避免频繁查询。
 */
function onSearchInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    page.value = 1
    loadQuestions()
  }, 300)
}

/** 分类切换时重新加载 */
function onCategoryChange() {
  page.value = 1
  loadQuestions()
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

onMounted(() => {
  loadQuestions()
})
</script>

<template>
  <div class="space-y-4">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">📋 问题历史</h1>
      <span class="text-sm text-slate-400 dark:text-slate-500">共 {{ total }} 条记录</span>
    </div>

    <!-- 搜索 + 分类筛选 -->
    <div class="flex flex-col sm:flex-row gap-3">
      <!-- 搜索框 -->
      <div class="relative flex-1">
        <svg
          class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 dark:text-slate-500"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索问题关键词..."
          class="w-full pl-10 pr-4 py-2.5 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg
                 text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500
                 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 focus:border-transparent
                 transition-all"
          @input="onSearchInput"
        />
        <!-- 清除搜索按钮 -->
        <button
          v-if="searchQuery"
          class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
          @click="searchQuery = ''; onSearchInput()"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 分类下拉 -->
      <select
        v-model="selectedCategory"
        class="px-4 py-2.5 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg
               text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400
               cursor-pointer transition-all appearance-none bg-no-repeat"
        style="background-image: url(&quot;data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e&quot;); background-position: right 0.5rem center; background-size: 1.5em 1.5em; padding-right: 2.5rem;"
        @change="onCategoryChange"
      >
        <option v-for="cat in CATEGORIES" :key="cat" :value="cat">
          {{ cat === '全部' ? '📂 全部分类' : cat }}
        </option>
      </select>
    </div>

    <!-- 骨架屏加载 -->
    <SkeletonLoader v-if="isLoading && questions.length === 0" type="list" />

    <!-- 空状态 -->
    <div v-else-if="questions.length === 0" class="text-center py-16">
      <p class="text-5xl mb-4">📭</p>
      <p class="text-slate-500 dark:text-slate-400 mb-4">
        {{ searchQuery || selectedCategory !== '全部' ? '没有匹配的记录，试试其他关键词或分类' : '还没有提问记录' }}
      </p>
      <router-link
        to="/"
        class="inline-block px-5 py-2 bg-indigo-600 dark:bg-indigo-500 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 dark:hover:bg-indigo-600 transition-colors"
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

          <!-- 底部：分类标签 + 时间 -->
          <div class="flex items-center gap-2">
            <span
              v-if="q.category && q.category !== '分析中...'"
              class="text-xs px-2 py-0.5 rounded-full bg-white/60 dark:bg-slate-800/60"
              :class="metaClass(idx)"
            >
              {{ q.category }}
            </span>
            <span class="text-xs opacity-50" :class="metaClass(idx)">
              {{ formatTime(q.created_at) }}
            </span>
          </div>

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
            class="absolute -top-1 -left-1 opacity-0 group-hover:opacity-100 transition-all duration-300 text-slate-300 dark:text-slate-600 hover:text-red-500 dark:hover:text-red-400 p-1"
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
        class="px-6 py-2 text-sm text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-900 transition-colors"
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
