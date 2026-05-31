<!--
  全局导航栏组件
  业务角色：页面顶部导航，提供各功能页面的快捷入口。
  当前路由高亮显示，帮助用户感知当前位置。
-->
<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

/** 导航项配置 — 对应4个核心业务页面 */
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
  <nav class="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
    <div class="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
      <!-- Logo区域 — 品牌标识 -->
      <router-link to="/" class="flex items-center gap-2 font-bold text-lg text-indigo-600 hover:text-indigo-700 transition-colors">
        <span class="text-2xl">🪞</span>
        <span>Mirro</span>
      </router-link>

      <!-- 导航链接 — 各业务页面入口 -->
      <div class="flex items-center gap-1">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
          :class="isActive(item.path)
            ? 'bg-indigo-50 text-indigo-700'
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'"
          :title="item.desc"
        >
          {{ item.label }}
        </router-link>
      </div>
    </div>
  </nav>
</template>
