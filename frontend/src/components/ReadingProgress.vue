<!--
  阅读进度条 + 回到顶部按钮
  业务角色：增强长内容页面的导航体验。
  - 顶部细进度条显示当前阅读位置
  - 右下角FAB按钮一键回到顶部（滚动超过400px显示）
-->
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

/** 阅读进度百分比 (0-100) */
const progress = ref(0)
/** 是否显示回到顶部按钮 */
const showBackTop = ref(false)
/** 进度条宽度样式 */
const barWidth = computed(() => `${progress.value}%`)

function onScroll() {
  const scrollTop = window.scrollY
  const docHeight = document.documentElement.scrollHeight - window.innerHeight
  progress.value = docHeight > 0 ? Math.min((scrollTop / docHeight) * 100, 100) : 0
  showBackTop.value = scrollTop > 400
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

let ticking = false
function handleScroll() {
  if (!ticking) {
    requestAnimationFrame(() => {
      onScroll()
      ticking = false
    })
    ticking = true
  }
}

onMounted(() => window.addEventListener('scroll', handleScroll, { passive: true }))
onUnmounted(() => window.removeEventListener('scroll', handleScroll))
</script>

<template>
  <!-- 阅读进度条 — 固定在页面最顶部，z-60高于导航栏 -->
  <div
    class="fixed top-0 left-0 z-[60] h-[3px] pointer-events-none transition-[width] duration-150 ease-out"
    :style="{ background: 'linear-gradient(90deg, #6366f1, #a855f7, #ec4899)', width: barWidth }"
  />

  <!-- 回到顶部 FAB -->
  <Transition name="fab">
    <button
      v-if="showBackTop"
      class="fixed bottom-24 right-6 z-40 w-10 h-10 rounded-full
             bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700
             text-slate-500 dark:text-slate-400 shadow-lg
             hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400
             hover:shadow-xl active:scale-90 transition-all duration-200
             flex items-center justify-center"
      title="回到顶部"
      @click="scrollToTop"
    >
      <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 15l-6-6-6 6"/>
      </svg>
    </button>
  </Transition>
</template>

<style scoped>
.fab-enter-active {
  transition: all 0.25s ease-out;
}
.fab-leave-active {
  transition: all 0.2s ease-in;
}
.fab-enter-from,
.fab-leave-to {
  opacity: 0;
  transform: translateY(1rem) scale(0.8);
}
</style>
