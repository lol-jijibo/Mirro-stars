<!--
  Mirro 根组件 — 应用外壳
  业务角色：提供全局布局框架（导航栏 + 内容区），所有页面在此插槽内渲染。
  管理暗色模式状态：读取 localStorage 偏好，监听系统主题变化，应用到 <html> 元素。
-->
<script setup lang="ts">
import { ref, onMounted, provide } from 'vue'
import NavBar from '@/components/NavBar.vue'

/** 当前是否为暗色模式 */
const isDark = ref(false)

/** 暗色模式切换函数（通过 provide 注入给子组件） */
function toggleDark() {
  isDark.value = !isDark.value
  applyDarkMode()
  localStorage.setItem('mirro-dark-mode', isDark.value ? 'dark' : 'light')
}

/** 应用暗色模式到 DOM */
function applyDarkMode() {
  const html = document.documentElement
  if (isDark.value) {
    html.classList.add('dark')
  } else {
    html.classList.remove('dark')
  }
}

/** 初始化暗色模式：localStorage > 系统偏好 > 默认关闭 */
function initDarkMode() {
  const stored = localStorage.getItem('mirro-dark-mode')
  if (stored === 'dark') {
    isDark.value = true
  } else if (stored === 'light') {
    isDark.value = false
  } else {
    // 没有存储偏好时，跟随系统
    isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }
  applyDarkMode()

  // 监听系统主题变化（仅当没有手动设置时生效）
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem('mirro-dark-mode')) {
      isDark.value = e.matches
      applyDarkMode()
    }
  })
}

// 注入给子组件使用
provide('isDark', isDark)
provide('toggleDark', toggleDark)

onMounted(() => {
  initDarkMode()
})
</script>

<template>
  <!-- 全局布局：顶部导航 + 主内容区 -->
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900 transition-colors duration-300">
    <NavBar :is-dark="isDark" @toggle-dark="toggleDark" />
    <main class="max-w-6xl mx-auto px-4 py-8 page-container">
      <!-- 页面主体：直接渲染当前路由，避免异常恢复时路由内容被过渡状态吞掉 -->
      <router-view />
    </main>

    <!-- 页脚 — 项目标识 -->
    <footer class="text-center py-6 text-sm text-slate-400 dark:text-slate-600">
      Mirro AI — 面向年轻人的智能问题解决引擎
    </footer>
  </div>
</template>

<style>
/* ========== 页面过渡动画 ==========
   策略：入场用轻微上滑+淡入，出场用淡出，两者同时进行，
   营造文字从下方缓缓浮现的自然质感，不拖沓。
   GPU 加速：仅使用 opacity + transform，不触发 layout。
   cubic-bezier(0.4, 0, 0.2, 1) = Material Design 标准缓出曲线。
*/

.page-container {
  position: relative;
}

/* 入场：280ms，文字缓缓浮现 + 轻微上浮 */
.page-enter-active {
  transition: opacity 0.28s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  will-change: opacity, transform;
}

/* 出场：180ms，比入场快一点，不抢戏 */
.page-leave-active {
  transition: opacity 0.18s cubic-bezier(0.4, 0, 1, 1);
  will-change: opacity;
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
}

/* 首次进入页面时不做位移，只淡入 */
.page-appear-active {
  transition: opacity 0.3s ease-out;
}
.page-appear-from {
  opacity: 0;
  transform: none;
}
</style>
