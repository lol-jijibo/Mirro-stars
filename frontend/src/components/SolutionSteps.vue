<!--
  分步执行计划组件
  业务角色：将AI生成的解决步骤以时间轴卡片形式展示。
  每个步骤显示序号、标题、描述和预计耗时，用户可以按顺序执行。
-->
<script setup lang="ts">
import type { SolutionStep } from '@/types'

defineProps<{
  /** 分步执行计划列表 */
  steps: SolutionStep[]
}>()
</script>

<template>
  <div class="bg-white rounded-xl border border-slate-200 overflow-hidden">
    <!-- 标题栏 -->
    <div class="px-5 py-3 border-b border-slate-100 bg-emerald-50/50">
      <h3 class="font-semibold text-sm text-emerald-700">📋 共 {{ steps.length }} 步</h3>
    </div>

    <!-- 步骤时间轴 -->
    <div class="p-5">
      <div v-if="steps.length === 0" class="text-center py-4 text-slate-400 text-sm">
        等待执行计划生成中...
      </div>

      <!-- 时间轴布局 — 竖线+步骤卡片 -->
      <div v-else class="relative">
        <!-- 左侧竖线 -->
        <div class="absolute left-5 top-0 bottom-0 w-0.5 bg-emerald-200" />

        <div
          v-for="s in steps"
          :key="s.step"
          class="relative pl-12 pb-5 last:pb-0"
        >
          <!-- 步骤序号圆点 -->
          <div class="absolute left-3.5 w-3 h-3 rounded-full bg-emerald-500 ring-4 ring-emerald-100 z-10" />

          <!-- 步骤卡片 -->
          <div class="bg-slate-50 rounded-lg p-4 hover:bg-emerald-50/50 transition-colors">
            <div class="flex items-center justify-between mb-1">
              <h4 class="font-semibold text-slate-800">
                第{{ s.step }}步：{{ s.title }}
              </h4>
              <span class="text-xs text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded-full font-medium">
                ⏱ {{ s.duration }}
              </span>
            </div>
            <p class="text-sm text-slate-600 leading-relaxed">{{ s.description }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
