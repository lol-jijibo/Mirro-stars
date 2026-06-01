<!--
  全局导航栏组件
  业务角色：页面顶部导航，提供各功能页面的快捷入口 + 暗色模式切换。
  当前路由高亮显示，帮助用户感知当前位置。
-->
<script setup lang="ts">
import { useRoute } from 'vue-router'

defineProps<{
  /** 当前是否为暗色模式 */
  isDark?: boolean
}>()

defineEmits<{
  /** 切换暗色模式 */
  toggleDark: []
}>()

const route = useRoute()

/** 导航项配置 — 对应3个核心业务页面 */
const navItems = [
  { path: '/', label: '🔍 提问', desc: '提交新问题' },
  { path: '/history', label: '📋 历史', desc: '查看提问记录' },
  { path: '/dashboard', label: '📊 看板', desc: '问题统计' },
]

/** 判断当前路由是否匹配导航项 */
function isActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<template>
  <nav class="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-700 transition-colors">
    <div class="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
      <!-- Logo区域 — 品牌标识 -->
      <router-link to="/" class="flex items-center gap-2 font-bold text-lg text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors">
        <span class="text-2xl">🪞</span>
        <span>Mirro</span>
      </router-link>

      <!-- 导航链接 + 暗色模式切换 -->
      <div class="flex items-center gap-1">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
          :class="isActive(item.path)
            ? 'bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
            : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'"
          :title="item.desc"
        >
          {{ item.label }}
        </router-link>

        <!-- 暗色模式切换按钮 -->
        <button
          class="ml-2 p-2 rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          :title="isDark ? '切换到亮色模式' : '切换到暗色模式'"
          @click="$emit('toggleDark')"
        >
          <!-- 太阳图标（亮色模式下显示） -->
          <svg v-if="!isDark" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
          <!-- 月亮图标（暗色模式下显示） -->
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
          </svg>
        </button>
      </div>
    </div>
  </nav>
</template>
