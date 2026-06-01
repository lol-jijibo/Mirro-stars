<!--
  骨架屏加载组件
  业务角色：在AI答案生成/数据加载期间展示占位动画，提升感知性能。
  用户等待时看到shimmer动画，比空白页面或转圈更有产品感。
-->
<script setup lang="ts">
defineProps<{
  /** 骨架屏类型：answer-答案页 / list-列表页 / card-卡片 */
  type?: 'answer' | 'list' | 'card'
}>()
</script>

<template>
  <!-- 答案页骨架屏 — 模拟Markdown内容结构 -->
  <div v-if="type === 'answer'" class="space-y-4 animate-pulse">
    <div class="skeleton-shimmer dark:skeleton-shimmer-dark h-6 w-3/4 rounded" />
    <div class="skeleton-shimmer dark:skeleton-shimmer-dark h-4 w-full rounded" />
    <div class="skeleton-shimmer dark:skeleton-shimmer-dark h-4 w-5/6 rounded" />
    <div class="skeleton-shimmer dark:skeleton-shimmer-dark h-4 w-4/5 rounded" />
    <div class="skeleton-shimmer dark:skeleton-shimmer-dark h-40 w-full rounded-lg mt-6" />
    <div class="skeleton-shimmer dark:skeleton-shimmer-dark h-4 w-2/3 rounded" />
    <div class="skeleton-shimmer dark:skeleton-shimmer-dark h-4 w-3/4 rounded" />
  </div>

  <!-- 列表页骨架屏 — 模拟多行记录 -->
  <div v-else-if="type === 'list'" class="space-y-3">
    <div v-for="i in 5" :key="i" class="skeleton-shimmer dark:skeleton-shimmer-dark h-16 w-full rounded-lg" />
  </div>

  <!-- 卡片骨架屏 — 单张卡片 -->
  <div v-else class="skeleton-shimmer dark:skeleton-shimmer-dark h-48 w-full rounded-xl" />
</template>
