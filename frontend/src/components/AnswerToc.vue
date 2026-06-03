<!--
  答案目录导航 (Table of Contents)
  业务角色：为长答案提供快速导航，提取Markdown标题生成浮动目录。
  - 自动解析h2/h3/h4标题
  - IntersectionObserver 高亮当前阅读位置
  - 仅在大屏(xl)显示，小屏隐藏
  - 仅有2个以上标题时才显示
-->
<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue'

const props = defineProps<{
  /** Markdown原文，用于提取标题 */
  content: string
  /** 答案是否已生成完毕 */
  isDone: boolean
}>()

interface TocItem {
  id: string
  text: string
  level: 2 | 3 | 4
}

/** 当前活跃的标题id */
const activeId = ref('')

/** 从Markdown中提取h2/h3/h4标题 */
const headings = computed<TocItem[]>(() => {
  if (!props.content) return []
  const items: TocItem[] = []
  const regex = /^(#{2,4})\s+(.+)$/gm
  let match
  while ((match = regex.exec(props.content)) !== null) {
    const text = match[2].trim().replace(/[\\`*_{}[\]()#+\-.!|~]/g, '')
    // 去掉可能残留的markdown格式
    const id = text
      .replace(/\s+/g, '-')
      .replace(/[^\w\u4e00-\u9fa5-]/g, '')
      .toLowerCase()
      .slice(0, 60)
    if (id && text.length > 1) {
      items.push({ id, text, level: match[1].length as 2 | 3 | 4 })
    }
  }
  return items
})

/** 是否显示TOC */
const visible = computed(() => {
  return props.isDone && headings.value.length >= 2
})

/** 滚动到指定标题 */
function scrollTo(id: string) {
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    activeId.value = id
  }
}

// ====== IntersectionObserver 监听标题可见性 ======
let observer: IntersectionObserver | null = null

function setupObserver() {
  teardownObserver()
  if (!props.isDone) return

  nextTick(() => {
    const elements = headings.value
      .map(h => document.getElementById(h.id))
      .filter(Boolean) as HTMLElement[]

    if (elements.length === 0) return

    // 收集所有进入视口的标题，取最靠上的一个
    const visibleSet = new Map<string, number>()
    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            visibleSet.set(entry.target.id, entry.boundingClientRect.top)
          } else {
            visibleSet.delete(entry.target.id)
          }
        }
        // 选择top最小的（最靠上的可见标题）
        let minTop = Infinity
        let minId = ''
        for (const [id, top] of visibleSet) {
          if (top < minTop) { minTop = top; minId = id }
        }
        if (minId) activeId.value = minId
      },
      { rootMargin: '-80px 0px -70% 0px', threshold: 0 },
    )

    elements.forEach(el => observer!.observe(el))
  })
}

function teardownObserver() {
  if (observer) { observer.disconnect(); observer = null }
}

watch(() => props.isDone, (done) => { if (done) setupObserver() })
onMounted(() => { if (props.isDone) setupObserver() })
onUnmounted(teardownObserver)
</script>

<template>
  <Transition name="toc-slide">
    <nav
      v-if="visible"
      class="hidden xl:block fixed top-24 z-30 w-48"
      style="left: max(1rem, calc((100vw - 60rem) / 2 - 13rem)); max-height: calc(100vh - 8rem);"
    >
      <div class="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3">
        目录
      </div>
      <ul class="space-y-1.5 overflow-y-auto" style="max-height: calc(100vh - 12rem);">
        <li
          v-for="heading in headings"
          :key="heading.id"
        >
          <button
            class="block w-full text-left text-sm leading-snug py-1 px-2 rounded-md border-l-2 transition-all duration-150 truncate"
            :class="[
              heading.level === 3 ? 'pl-4' : '',
              heading.level === 4 ? 'pl-6' : '',
              activeId === heading.id
                ? 'border-indigo-500 text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/60 font-medium'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/50',
            ]"
            :title="heading.text"
            @click="scrollTo(heading.id)"
          >
            {{ heading.text }}
          </button>
        </li>
      </ul>
    </nav>
  </Transition>
</template>

<style scoped>
.toc-slide-enter-active {
  transition: all 0.3s ease-out;
}
.toc-slide-leave-active {
  transition: all 0.2s ease-in;
}
.toc-slide-enter-from,
.toc-slide-leave-to {
  opacity: 0;
  transform: translateX(0.5rem);
}
</style>
