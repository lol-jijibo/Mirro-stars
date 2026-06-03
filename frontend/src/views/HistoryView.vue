<!--
  问题历史列表页 — 查看所有提问记录
  业务角色：用户在此浏览、回顾、删除历史提问。
  支持分页加载、关键词搜索、分类筛选，按时间倒序排列，点击可进入详情页。
-->
<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchQuestions, deleteQuestion, batchDeleteQuestions, fetchStats, updateQuestionCategory } from '@/api/client'
import type { QuestionResponse } from '@/types'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const router = useRouter()

/** 8个预设分类（与后端AI分类体系一致），每项配有图标与专属色 */
const CATEGORIES = [
  { name: '全部', icon: '📂', color: 'slate' },
  { name: '职业发展', icon: '💼', color: 'indigo' },
  { name: '情感关系', icon: '💕', color: 'rose' },
  { name: '个人成长', icon: '🌱', color: 'emerald' },
  { name: '理财规划', icon: '💰', color: 'amber' },
  { name: '健康生活', icon: '🏃', color: 'sky' },
  { name: '社交技巧', icon: '🤝', color: 'purple' },
  { name: '技术学习', icon: '💻', color: 'cyan' },
  { name: '其他', icon: '📌', color: 'warm' },
]

/** 历史问题列表 */
const questions = ref<QuestionResponse[]>([])
/** 问题总数 */
const total = ref(0)
/** 当前页码 */
const page = ref(1)
/** 每页条数 */
const pageSize = ref(20)
/** 每页条数选项 */
const pageSizeOptions = [5, 10, 20]
/** 总页数 */
const totalPages = ref(0)
/** 是否加载中 */
const isLoading = ref(false)
/** 搜索关键词 */
const searchQuery = ref('')
/** 分类筛选（"全部"表示不过滤） */
const selectedCategory = ref('全部')
/** 下拉菜单是否展开 */
const isDropdownOpen = ref(false)
/** 下拉触发器引用（用于点击外部关闭） */
const dropdownRef = ref<HTMLElement | null>(null)

/** 批量模式 */
const isBatchMode = ref(false)
/** 已勾选的ID集合 */
const selectedIds = ref<Set<string>>(new Set())
/** 批量删除确认 */
const pendingBatchDelete = ref(false)
/** 各分类问题数量 */
const categoryCounts = ref<Record<string, number>>({})

// ========== 分类标签编辑 ==========
/** 8个有效分类（不含"全部"） */
const CATEGORY_OPTIONS = CATEGORIES.filter(c => c.name !== '全部')
/** 当前正在编辑分类的问题ID（null = 无展开的下拉菜单） */
const editingCategoryId = ref<string | null>(null)
/** 下拉方向：true = 向上弹出，false = 向下弹出 */
const dropUp = ref(true)
/** 延迟关闭定时器 */
let categoryCloseTimer: ReturnType<typeof setTimeout> | null = null

/** 鼠标移入标签 → 检测空间并展开下拉 */
function showCategoryEdit(questionId: string, event: MouseEvent) {
  if (categoryCloseTimer) {
    clearTimeout(categoryCloseTimer)
    categoryCloseTimer = null
  }
  // 检测标签上方是否有足够空间容纳下拉菜单（约需 260px）
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  dropUp.value = rect.top > 280
  editingCategoryId.value = questionId
}

/** 鼠标移出标签/下拉区域 → 延迟关闭（给鼠标移动到下拉菜单留时间） */
function hideCategoryEdit() {
  categoryCloseTimer = setTimeout(() => {
    editingCategoryId.value = null
  }, 150)
}

/** 选择新分类并提交 */
async function selectCardCategory(questionId: string, category: string) {
  editingCategoryId.value = null
  // 乐观更新：立即更新本地列表
  const q = questions.value.find(q => q.id === questionId)
  if (q) q.category = category
  try {
    await updateQuestionCategory(questionId, category)
  } catch {
    // 更新失败静默，本地已乐观更新
  }
}

/** 当前选中的分类对象 */
const selectedCat = ref(CATEGORIES[0])

/** 分类色彩映射 — 每种分类专用的色调 */
const colorMap: Record<string, { soft: string; text: string; hoverBg: string; dot: string; accent: string }> = {
  slate:    { soft: 'bg-slate-50 dark:bg-slate-800/60', text: 'text-slate-700 dark:text-slate-300', hoverBg: 'hover:bg-slate-100 dark:hover:bg-slate-700/60', dot: 'bg-slate-400', accent: 'text-slate-500 dark:text-slate-400' },
  indigo:   { soft: 'bg-indigo-50 dark:bg-indigo-950/60', text: 'text-indigo-700 dark:text-indigo-300', hoverBg: 'hover:bg-indigo-100 dark:hover:bg-indigo-900/40', dot: 'bg-indigo-400', accent: 'text-indigo-500 dark:text-indigo-400' },
  rose:     { soft: 'bg-rose-50 dark:bg-rose-950/60', text: 'text-rose-700 dark:text-rose-300', hoverBg: 'hover:bg-rose-100 dark:hover:bg-rose-900/40', dot: 'bg-rose-400', accent: 'text-rose-500 dark:text-rose-400' },
  emerald:  { soft: 'bg-emerald-50 dark:bg-emerald-950/60', text: 'text-emerald-700 dark:text-emerald-300', hoverBg: 'hover:bg-emerald-100 dark:hover:bg-emerald-900/40', dot: 'bg-emerald-400', accent: 'text-emerald-500 dark:text-emerald-400' },
  amber:    { soft: 'bg-amber-50 dark:bg-amber-950/60', text: 'text-amber-700 dark:text-amber-300', hoverBg: 'hover:bg-amber-100 dark:hover:bg-amber-900/40', dot: 'bg-amber-400', accent: 'text-amber-500 dark:text-amber-400' },
  sky:      { soft: 'bg-sky-50 dark:bg-sky-950/60', text: 'text-sky-700 dark:text-sky-300', hoverBg: 'hover:bg-sky-100 dark:hover:bg-sky-900/40', dot: 'bg-sky-400', accent: 'text-sky-500 dark:text-sky-400' },
  purple:   { soft: 'bg-purple-50 dark:bg-purple-950/60', text: 'text-purple-700 dark:text-purple-300', hoverBg: 'hover:bg-purple-100 dark:hover:bg-purple-900/40', dot: 'bg-purple-400', accent: 'text-purple-500 dark:text-purple-400' },
  cyan:     { soft: 'bg-cyan-50 dark:bg-cyan-950/60', text: 'text-cyan-700 dark:text-cyan-300', hoverBg: 'hover:bg-cyan-100 dark:hover:bg-cyan-900/40', dot: 'bg-cyan-400', accent: 'text-cyan-500 dark:text-cyan-400' },
  warm:     { soft: 'bg-stone-50 dark:bg-stone-800/60', text: 'text-stone-700 dark:text-stone-300', hoverBg: 'hover:bg-stone-100 dark:hover:bg-stone-700/60', dot: 'bg-stone-400', accent: 'text-stone-500 dark:text-stone-400' },
}

function catColor(cat: typeof CATEGORIES[0]) { return colorMap[cat.color] }

/** 展开/收起下拉菜单 */
function toggleDropdown() {
  isDropdownOpen.value = !isDropdownOpen.value
}

/** 关闭下拉菜单 */
function closeDropdown() {
  isDropdownOpen.value = false
}

/** 选择分类 */
function selectCategory(cat: typeof CATEGORIES[0]) {
  selectedCategory.value = cat.name
  selectedCat.value = cat
  closeDropdown()
  onCategoryChange()
}

/** 点击外部关闭下拉菜单 */
function onWindowClick(e: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    closeDropdown()
  }
}
/** 防抖定时器 */
let debounceTimer: ReturnType<typeof setTimeout> | null = null
/** AbortController — 组件卸载时取消未完成的请求 */
let abortController: AbortController | null = null

/**
 * 加载问题历史列表
 * 业务场景：首次进入页面、翻页、搜索、筛选时加载问题记录。
 */
async function loadQuestions() {
  // 取消上一次未完成的请求，避免旧请求覆盖新数据
  if (abortController) {
    abortController.abort()
  }
  abortController = new AbortController()
  const signal = abortController.signal

  isLoading.value = true
  try {
    const search = searchQuery.value.trim()
    const category = selectedCategory.value === '全部' ? '' : selectedCategory.value
    const data = await fetchQuestions(page.value, pageSize.value, search, category, '', signal)
    questions.value = data.items
    total.value = data.total
    totalPages.value = Math.ceil(data.total / pageSize.value)
  } catch (err: any) {
    // AbortError 是正常取消，不打印错误
    if (err?.name !== 'AbortError') {
      // 加载失败静默
    }
  } finally {
    isLoading.value = false
  }
}

/** 跳转到指定页码 */
function goToPage(p: number) {
  if (p < 1 || p > totalPages.value || p === page.value) return
  page.value = p
  loadQuestions()
}

/** 切换每页条数 */
function changePageSize(size: number) {
  if (size === pageSize.value) return
  pageSize.value = size
  page.value = 1
  loadQuestions()
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

/** 待确认删除的问题ID（null表示无待确认项） */
const pendingDeleteId = ref<string | null>(null)

/**
 * 第一步：点击删除按钮，进入确认状态
 * 业务场景：防止用户误删，需要二次确认后才执行删除。
 */
function requestDelete(id: string) {
  pendingDeleteId.value = id
}

/** 取消删除确认 */
function cancelDelete() {
  pendingDeleteId.value = null
}

/**
 * 第二步：确认删除问题记录
 * 业务场景：用户确认后执行实际删除操作。
 */
async function handleDelete(id: string) {
  try {
    await deleteQuestion(id)
    questions.value = questions.value.filter(q => q.id !== id)
    total.value--
  } catch {
    // 删除失败静默
  } finally {
    pendingDeleteId.value = null
  }
}

/** 切换批量模式 */
function toggleBatchMode() {
  isBatchMode.value = !isBatchMode.value
  if (!isBatchMode.value) selectedIds.value = new Set()
}

/** 全选/取消全选当前页 */
function toggleSelectAll() {
  if (selectedIds.value.size === questions.value.length) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(questions.value.map(q => q.id))
  }
}

/** 勾选/取消单个 */
function toggleSelect(id: string) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

/** 批量删除 */
function requestBatchDelete() {
  if (selectedIds.value.size === 0) return
  pendingBatchDelete.value = true
}

function cancelBatchDelete() {
  pendingBatchDelete.value = false
}

async function confirmBatchDelete() {
  const ids = [...selectedIds.value]
  try {
    await batchDeleteQuestions(ids)
    questions.value = questions.value.filter(q => !selectedIds.value.has(q.id))
    total.value -= ids.length
    totalPages.value = Math.ceil(total.value / pageSize.value)
    selectedIds.value = new Set()
    isBatchMode.value = false
  } catch {
    // 删除失败静默
  } finally {
    pendingBatchDelete.value = false
  }
}

/** 跳转到答案详情页 */
function goToQuestion(id: string) {
  if (isBatchMode.value) return // 批量模式下不跳转
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

/** 更新问题卡片阴影 */
function updateCardShadow(e: Event, shadow: string) {
  const target = e.currentTarget as HTMLElement | null
  if (target) target.style.boxShadow = shadow
}

/** AbortController for stats fetch — 独立于列表请求 */
let statsAbortController: AbortController | null = null

onMounted(async () => {
  loadQuestions()
  window.addEventListener('click', onWindowClick)
  // 加载各分类数量
  if (statsAbortController) statsAbortController.abort()
  statsAbortController = new AbortController()
  try {
    const stats = await fetchStats(statsAbortController.signal)
    for (const c of stats.categories) {
      categoryCounts.value[c.name] = c.count
    }
  } catch (err: any) {
    if (err?.name !== 'AbortError') { /* 静默 */ }
  }
})

onUnmounted(() => {
  window.removeEventListener('click', onWindowClick)
  // 取消所有未完成的请求
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  if (statsAbortController) {
    statsAbortController.abort()
    statsAbortController = null
  }
})
</script>

<template>
  <div class="space-y-4">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">📋 问题历史</h1>
        <!-- 批量管理按钮 -->
        <button
          class="px-3 py-1.5 text-xs font-medium rounded-lg border transition-all duration-200"
          :class="isBatchMode
            ? 'bg-indigo-50 dark:bg-indigo-950 border-indigo-200 dark:border-indigo-800 text-indigo-600 dark:text-indigo-400'
            : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-500'"
          @click="toggleBatchMode"
        >
          {{ isBatchMode ? '✓ 退出管理' : '☐ 批量管理' }}
        </button>
      </div>
      <span class="text-sm text-slate-400 dark:text-slate-500">共 {{ total }} 条记录</span>
    </div>

    <!-- 搜索 + 分类筛选 — 同一行 -->
    <div class="flex gap-3">
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
      <div ref="dropdownRef" class="relative flex-shrink-0">
        <!-- 触发器按钮 -->
        <button
          class="flex items-center gap-2 px-4 py-2.5 text-sm font-medium bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl
                 text-slate-700 dark:text-slate-300 hover:border-slate-300 dark:hover:border-slate-600
                 shadow-sm hover:shadow-md transition-all duration-200 select-none whitespace-nowrap"
          @click.stop="toggleDropdown"
        >
          <!-- 当前选中图标 -->
          <span class="text-base leading-none">{{ selectedCat.icon }}</span>
          <!-- 当前选中名称 -->
          <span :class="catColor(selectedCat).text">{{ selectedCat.name }}</span>
          <!-- 箭头 — 展开时旋转180° -->
          <svg
            class="w-4 h-4 ml-auto text-slate-400 dark:text-slate-500 transition-transform duration-300"
            :class="{ 'rotate-180': isDropdownOpen }"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <!-- 下拉菜单面板 -->
        <Transition name="dropdown">
          <div
            v-if="isDropdownOpen"
            class="absolute right-0 sm:min-w-[220px] mt-2 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl dark:shadow-2xl z-20 origin-top"
            style="box-shadow: 0 16px 48px rgba(0,0,0,0.10), 0 4px 12px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.03);"
          >
            <button
              v-for="cat in CATEGORIES"
              :key="cat.name"
              class="flex items-center gap-2 w-full px-4 py-2.5 text-sm transition-all duration-150 select-none"
              :class="[
                selectedCategory === cat.name
                  ? [catColor(cat).soft, catColor(cat).text, 'font-semibold']
                  : [catColor(cat).text, 'font-normal', catColor(cat).hoverBg, 'hover:pl-5'],
              ]"
              @click.stop="selectCategory(cat)"
            >
              <!-- 图标 -->
              <span class="text-base leading-none flex-shrink-0">{{ cat.icon }}</span>
              <!-- 名称 + 条数 -->
              <span class="flex-1 text-left">{{ cat.name }}<span v-if="cat.name !== '全部'" class="ml-1 opacity-50 text-xs">({{ categoryCounts[cat.name] || 0 }})</span></span>
              <!-- 选中勾号 -->
              <svg
                v-if="selectedCategory === cat.name"
                class="w-4 h-4 flex-shrink-0"
                :class="catColor(cat).accent"
                fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </button>
          </div>
        </Transition>
      </div>
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
        class="group relative rounded-2xl px-6 py-5 transition-all duration-500 hover:-translate-y-1 hover:scale-[1.01]"
        :class="[gradientClass(idx), isBatchMode ? 'cursor-default' : 'cursor-pointer']"
        :style="{
          zIndex: editingCategoryId === q.id ? 50 : undefined,
          boxShadow: cardShadow(idx),
          animationDelay: `${idx * 60}ms`,
          animation: 'fadeInUp 0.4s ease-out both',
        }"
        @click="isBatchMode ? toggleSelect(q.id) : goToQuestion(q.id)"
        @mouseenter="updateCardShadow($event, cardHoverShadow(idx))"
        @mouseleave="updateCardShadow($event, cardShadow(idx))"
      >
        <!-- 背景光晕 -->
        <div
          class="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
          :class="glowClass(idx)"
        />

        <!-- 内容区 — 居中布局 -->
        <div class="relative flex flex-col items-center text-center gap-3">
          <!-- 批量勾选框 -->
          <div
            v-if="isBatchMode"
            class="absolute -top-1 -left-1 z-10 transition-all duration-200"
            @click.stop="toggleSelect(q.id)"
          >
            <div
              class="w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all duration-200"
              :class="selectedIds.has(q.id)
                ? 'bg-indigo-500 border-indigo-500 shadow-sm shadow-indigo-500/30'
                : 'bg-white dark:bg-slate-700 border-slate-300 dark:border-slate-600'"
            >
              <svg
                v-if="selectedIds.has(q.id)"
                class="w-3 h-3 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>

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

          <!-- 底部：分类标签（hover 修改） + 时间 -->
          <div class="flex items-center gap-2" @click.stop>
            <!-- 分类标签 — 鼠标移入弹出下拉菜单，移出自动消失 -->
            <div
              class="relative"
              @mouseenter="showCategoryEdit(q.id, $event)"
              @mouseleave="hideCategoryEdit"
            >
              <span
                v-if="q.category && q.category !== '分析中...'"
                class="inline-flex items-center text-xs px-2 py-0.5 rounded-full bg-white/60 dark:bg-slate-800/60
                       transition-all duration-150 cursor-default"
                :class="[
                  metaClass(idx),
                  editingCategoryId === q.id
                    ? 'ring-2 ring-offset-1 ring-indigo-300 dark:ring-indigo-600'
                    : ''
                ]"
              >
                {{ q.category }}
                <span class="ml-0.5 opacity-40 text-[10px]">▾</span>
              </span>
              <span
                v-else
                class="inline-flex items-center text-xs px-2 py-0.5 rounded-full bg-white/60 dark:bg-slate-800/60
                       transition-all duration-150 cursor-default"
                :class="[
                  metaClass(idx),
                  editingCategoryId === q.id
                    ? 'ring-2 ring-offset-1 ring-indigo-300 dark:ring-indigo-600'
                    : ''
                ]"
              >
                未分类
                <span class="ml-0.5 opacity-40 text-[10px]">▾</span>
              </span>

              <!-- 分类选择下拉菜单 -->
              <Transition name="cat-drop">
                <div
                  v-if="editingCategoryId === q.id"
                  :class="[
                    dropUp
                      ? 'bottom-full mb-1'
                      : 'top-full mt-1',
                    'absolute left-1/2 -translate-x-1/2 py-1 bg-white dark:bg-slate-800',
                    'border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl z-30 min-w-[130px]',
                  ]"
                  style="box-shadow: 0 12px 40px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.06);"
                >
                  <button
                    v-for="cat in CATEGORY_OPTIONS"
                    :key="cat.name"
                    class="flex items-center gap-2 w-full px-3 py-2 text-xs transition-all duration-100
                           hover:pl-4 whitespace-nowrap"
                    :class="[
                      q.category === cat.name
                        ? [catColor(cat).soft, catColor(cat).text, 'font-semibold']
                        : [catColor(cat).text, 'font-normal', catColor(cat).hoverBg],
                    ]"
                    @click.stop="selectCardCategory(q.id, cat.name)"
                  >
                    <span class="text-sm leading-none flex-shrink-0">{{ cat.icon }}</span>
                    <span>{{ cat.name }}</span>
                    <svg
                      v-if="q.category === cat.name"
                      class="w-3.5 h-3.5 ml-auto flex-shrink-0"
                      :class="catColor(cat).accent"
                      fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </button>
                </div>
              </Transition>
            </div>

            <span class="text-xs opacity-50" :class="metaClass(idx)">
              {{ formatTime(q.created_at) }}
            </span>
          </div>

          <!-- 删除按钮 — hover 时显示在右上角，独立于卡片点击区域 -->
          <button
            class="absolute -top-1 -right-1 opacity-0 group-hover:opacity-100 transition-all duration-300 p-1.5 rounded-lg
                   text-slate-400 dark:text-slate-500
                   hover:text-red-500 dark:hover:text-red-400
                   hover:bg-red-50 dark:hover:bg-red-950/60
                   cursor-pointer"
            title="删除此记录"
            @click.stop="requestDelete(q.id)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- 批量操作底部栏 -->
    <div
      v-if="isBatchMode && questions.length > 0"
      class="flex items-center justify-between px-4 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm"
    >
      <div class="flex items-center gap-3">
        <button
          class="text-sm text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          @click="toggleSelectAll"
        >
          {{ selectedIds.size === questions.length ? '取消全选' : '全选当前页' }}
        </button>
        <span class="text-sm text-slate-400 dark:text-slate-500">
          已选 <span class="font-semibold text-indigo-600 dark:text-indigo-400">{{ selectedIds.size }}</span> 条
        </span>
      </div>
      <button
        class="px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-xl shadow-sm shadow-red-500/25 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="selectedIds.size === 0"
        @click="requestBatchDelete"
      >
        🗑 批量删除
      </button>
    </div>

    <!-- 分页控件 -->
    <div v-if="totalPages > 0" class="flex items-center justify-between pt-1">
      <!-- 每页条数选择 -->
      <div class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <span>每页</span>
        <div class="flex gap-0.5 bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5">
          <button
            v-for="size in pageSizeOptions"
            :key="size"
            class="px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-200"
            :class="pageSize === size
              ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'"
            @click="changePageSize(size)"
          >
            {{ size }}
          </button>
        </div>
        <span>条</span>
      </div>

      <!-- 页码导航 -->
      <div class="flex items-center gap-1">
        <!-- 上一页 -->
        <button
          class="w-8 h-8 flex items-center justify-center rounded-lg text-sm transition-all duration-200"
          :class="page === 1
            ? 'text-slate-300 dark:text-slate-600 cursor-not-allowed'
            : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-indigo-600 dark:hover:text-indigo-400'"
          :disabled="page === 1"
          @click="goToPage(page - 1)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <!-- 页码数字 -->
        <template v-for="p in totalPages">
          <button
            v-if="p === 1 || p === totalPages || Math.abs(p - page) <= 1"
            :key="p"
            class="w-8 h-8 flex items-center justify-center rounded-lg text-sm font-medium transition-all duration-200"
            :class="p === page
              ? 'bg-indigo-500 text-white shadow-sm shadow-indigo-500/25'
              : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-300'"
            @click="goToPage(p)"
          >
            {{ p }}
          </button>
          <span
            v-else-if="p === 2 || p === totalPages - 1"
            :key="'dots-' + p"
            class="w-8 h-8 flex items-center justify-center text-xs text-slate-300 dark:text-slate-600"
          >…</span>
        </template>

        <!-- 下一页 -->
        <button
          class="w-8 h-8 flex items-center justify-center rounded-lg text-sm transition-all duration-200"
          :class="page === totalPages
            ? 'text-slate-300 dark:text-slate-600 cursor-not-allowed'
            : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-indigo-600 dark:hover:text-indigo-400'"
          :disabled="page === totalPages"
          @click="goToPage(page + 1)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 单条删除确认弹窗 -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="pendingDeleteId && !pendingBatchDelete"
          class="fixed inset-0 z-50 flex items-center justify-center p-4"
          @click.self="cancelDelete"
        >
          <div class="absolute inset-0 bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm" />
          <div class="relative bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-6 max-w-sm w-full text-center animate-pop-in">
            <div class="w-12 h-12 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-950 flex items-center justify-center">
              <svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-1">确认删除</h3>
            <p class="text-sm text-slate-500 dark:text-slate-400 mb-5">删除后无法恢复，确定要删除这条记录吗？</p>
            <div class="flex gap-3">
              <button
                class="flex-1 px-4 py-2.5 text-sm font-medium text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                @click="cancelDelete"
              >取消</button>
              <button
                class="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-xl shadow-sm shadow-red-500/25 transition-all active:scale-95"
                @click="pendingDeleteId && handleDelete(pendingDeleteId)"
              >确认删除</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 批量删除确认弹窗 -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="pendingBatchDelete"
          class="fixed inset-0 z-50 flex items-center justify-center p-4"
          @click.self="cancelBatchDelete"
        >
          <div class="absolute inset-0 bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm" />
          <div class="relative bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-6 max-w-sm w-full text-center animate-pop-in">
            <div class="w-12 h-12 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-950 flex items-center justify-center">
              <span class="text-xl">🗑</span>
            </div>
            <h3 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-1">批量删除</h3>
            <p class="text-sm text-slate-500 dark:text-slate-400 mb-5">
              确定要删除选中的 <span class="font-semibold text-red-500">{{ selectedIds.size }}</span> 条记录吗？删除后无法恢复。
            </p>
            <div class="flex gap-3">
              <button
                class="flex-1 px-4 py-2.5 text-sm font-medium text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                @click="cancelBatchDelete"
              >取消</button>
              <button
                class="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-xl shadow-sm shadow-red-500/25 transition-all active:scale-95"
                @click="confirmBatchDelete"
              >确认删除</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
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

/* 下拉菜单进出动画 */
.dropdown-enter-active {
  animation: dropdownIn 0.25s cubic-bezier(0.22, 0.61, 0.36, 1);
}
.dropdown-leave-active {
  animation: dropdownOut 0.18s cubic-bezier(0.55, 0.06, 0.68, 0.19);
}
@keyframes dropdownIn {
  from {
    opacity: 0;
    transform: translateY(-8px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
@keyframes dropdownOut {
  from {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateY(-8px) scale(0.96);
  }
}

/* 确认删除按钮弹入动画 */
@keyframes popIn {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
.animate-pop-in {
  animation: popIn 0.25s cubic-bezier(0.22, 0.61, 0.36, 1);
}

/* 模态弹窗进出动画 */
.modal-enter-active {
  transition: opacity 0.25s cubic-bezier(0.22, 0.61, 0.36, 1);
}
.modal-leave-active {
  transition: opacity 0.18s cubic-bezier(0.55, 0.06, 0.68, 0.19);
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

/* 分类编辑下拉菜单动画 */
.cat-drop-enter-active {
  transition: opacity 0.15s ease-out, transform 0.15s ease-out;
}
.cat-drop-leave-active {
  transition: opacity 0.1s ease-in, transform 0.1s ease-in;
}
.cat-drop-enter-from {
  opacity: 0;
  transform: translateY(4px) scale(0.95);
}
.cat-drop-leave-to {
  opacity: 0;
  transform: translateY(2px) scale(0.97);
}
</style>
