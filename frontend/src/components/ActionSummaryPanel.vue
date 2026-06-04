<!--
  回应要点面板
  业务角色：在长答案前按问题类型展示核心结论、理解要点、边界误区和延伸方向。
  帮助用户先抓住本题重点，再进入正文细读。
-->
<script setup lang="ts">
import { computed } from 'vue'
import type { ActionSummary } from '@/types'

const props = defineProps<{
  /** AI生成的顶部回应要点 */
  summary: ActionSummary
  /** 当前答案类型，用于切换回应要点的展示文案 */
  answerType: 'action' | 'insight'
}>()

const itemLabels = computed(() => {
  if (props.answerType === 'action') {
    return {
      conclusion: '核心结论',
      first: '下一步建议',
      timeframe: '推进节奏',
      risk: '主要风险',
      fitFor: '适合场景',
    }
  }

  return {
    conclusion: '关键结论',
    first: '核心理解',
    timeframe: '适用边界',
    risk: '常见误区',
    fitFor: '延伸思考',
  }
})
</script>

<template>
  <section class="bg-white dark:bg-slate-800 rounded-xl border border-indigo-100 dark:border-indigo-800 overflow-hidden">
    <div class="px-5 py-3 border-b border-indigo-100 dark:border-indigo-800 bg-indigo-50/70 dark:bg-indigo-950/50">
      <h2 class="text-sm font-semibold text-indigo-700 dark:text-indigo-300">回应要点</h2>
    </div>

    <div class="p-5 space-y-4">
      <div>
        <p class="text-xs font-medium text-slate-400 dark:text-slate-500 mb-1">{{ itemLabels.conclusion }}</p>
        <p class="text-base leading-relaxed text-slate-800 dark:text-slate-200">{{ summary.conclusion }}</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div class="rounded-lg bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-100 dark:border-emerald-800 p-3">
          <p class="text-xs font-medium text-emerald-600 dark:text-emerald-400 mb-1">{{ itemLabels.first }}</p>
          <p class="text-sm leading-relaxed text-emerald-900 dark:text-emerald-200">{{ summary.first_action }}</p>
        </div>

        <div class="rounded-lg bg-sky-50 dark:bg-sky-950/50 border border-sky-100 dark:border-sky-800 p-3">
          <p class="text-xs font-medium text-sky-600 dark:text-sky-400 mb-1">{{ itemLabels.timeframe }}</p>
          <p class="text-sm leading-relaxed text-sky-900 dark:text-sky-200">{{ summary.timeframe }}</p>
        </div>

        <div class="rounded-lg bg-amber-50 dark:bg-amber-950/50 border border-amber-100 dark:border-amber-800 p-3">
          <p class="text-xs font-medium text-amber-600 dark:text-amber-400 mb-1">{{ itemLabels.risk }}</p>
          <p class="text-sm leading-relaxed text-amber-900 dark:text-amber-200">{{ summary.risk }}</p>
        </div>

        <div class="rounded-lg bg-violet-50 dark:bg-violet-950/50 border border-violet-100 dark:border-violet-800 p-3">
          <p class="text-xs font-medium text-violet-600 dark:text-violet-400 mb-1">{{ itemLabels.fitFor }}</p>
          <p class="text-sm leading-relaxed text-violet-900 dark:text-violet-200">{{ summary.fit_for }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
