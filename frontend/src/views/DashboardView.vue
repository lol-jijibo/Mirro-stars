<!--
  统计看板页 — 问题数据分析
  业务角色：以图表形式展示用户提问的数据洞察。
  包含：问题分类饼图、每日提问趋势折线图、关键数据概览卡片。
  使用 ECharts（通过vue-echarts）渲染图表。
-->
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart, LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { StatsOverview } from '@/types'
import { fetchStats } from '@/api/client'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

// 按需注册ECharts组件（减小打包体积）
use([PieChart, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

/** 统计数据 */
const stats = ref<StatsOverview | null>(null)
/** 是否加载中 */
const isLoading = ref(false)

/**
 * 饼图配置 — 问题分类分布
 * 业务场景：展示哪些类型的问题最常被问到，帮助了解年轻人的关注点。
 */
const pieOption = computed(() => {
  if (!stats.value) return {}
  return {
    tooltip: { trigger: 'item' as const },
    legend: { bottom: '0%' },
    series: [{
      name: '问题分类',
      type: 'pie' as const,
      radius: ['45%', '75%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 6,
        borderColor: '#fff',
        borderWidth: 2,
      },
      label: { show: true, formatter: '{b}: {c}' },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' },
      },
      data: stats.value.categories.map(c => ({
        name: c.name,
        value: c.count,
      })),
      color: ['#6366f1', '#ec4899', '#22c55e', '#f59e0b', '#10b981', '#8b5cf6', '#94a3b8'],
    }],
  }
})

/**
 * 折线图配置 — 每日提问趋势
 * 业务场景：观察使用频率变化趋势。
 */
const lineOption = computed(() => {
  if (!stats.value) return {}
  const trend = stats.value.daily_trend
  return {
    tooltip: { trigger: 'axis' as const },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: trend.map(t => t.date.slice(5)),  // 只显示月-日
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value' as const,
      minInterval: 1,
    },
    series: [{
      name: '提问数',
      type: 'line' as const,
      data: trend.map(t => t.count),
      smooth: true,
      lineStyle: { color: '#6366f1', width: 2 },
      areaStyle: {
        color: {
          type: 'linear' as const,
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(99, 102, 241, 0.3)' },
            { offset: 1, color: 'rgba(99, 102, 241, 0.02)' },
          ],
        },
      },
      itemStyle: { color: '#6366f1' },
    }],
  }
})

onMounted(async () => {
  isLoading.value = true
  try {
    stats.value = await fetchStats()
  } catch {
    // 加载失败
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <h1 class="text-2xl font-bold text-slate-900">📊 统计看板</h1>

    <!-- 骨架屏 -->
    <SkeletonLoader v-if="isLoading" type="card" />

    <template v-else-if="stats">
      <!-- 数据概览卡片 — 总问题数、已解决数、解决率 -->
      <div class="grid grid-cols-3 gap-4">
        <div class="bg-white rounded-xl border border-slate-200 p-5 text-center">
          <p class="text-3xl font-bold text-indigo-600">{{ stats.total_questions }}</p>
          <p class="text-sm text-slate-500 mt-1">总提问数</p>
        </div>
        <div class="bg-white rounded-xl border border-slate-200 p-5 text-center">
          <p class="text-3xl font-bold text-emerald-600">{{ stats.total_answers }}</p>
          <p class="text-sm text-slate-500 mt-1">已解答</p>
        </div>
        <div class="bg-white rounded-xl border border-slate-200 p-5 text-center">
          <p class="text-3xl font-bold text-amber-600">
            {{ stats.total_questions > 0 ? Math.round(stats.total_answers / stats.total_questions * 100) : 0 }}%
          </p>
          <p class="text-sm text-slate-500 mt-1">解决率</p>
        </div>
      </div>

      <!-- 图表区域 — 饼图 + 折线图 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- 分类分布饼图 -->
        <div v-if="stats.categories.length > 0" class="bg-white rounded-xl border border-slate-200 p-5">
          <h3 class="font-semibold text-sm text-slate-700 mb-3">问题分类分布</h3>
          <VChart :option="pieOption" autoresize style="height: 320px" />
        </div>

        <!-- 每日趋势折线图 -->
        <div v-if="stats.daily_trend.length > 0" class="bg-white rounded-xl border border-slate-200 p-5">
          <h3 class="font-semibold text-sm text-slate-700 mb-3">每日提问趋势</h3>
          <VChart :option="lineOption" autoresize style="height: 320px" />
        </div>
      </div>
    </template>

    <!-- 空状态 -->
    <div v-else class="text-center py-16">
      <p class="text-5xl mb-4">📊</p>
      <p class="text-slate-500">暂无统计数据</p>
    </div>
  </div>
</template>
