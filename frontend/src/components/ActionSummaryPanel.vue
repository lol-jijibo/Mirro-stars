<!--
  行动摘要面板
  业务角色：在长答案前展示核心结论、第一步行动、周期、风险和适用场景。
  帮助用户先判断答案是否适合自己，再进入正文细读。
-->
<script setup lang="ts">
import type { ActionSummary } from '@/types'

defineProps<{
  /** AI生成的顶部行动摘要 */
  summary: ActionSummary
}>()
</script>

<template>
  <section class="bg-white dark:bg-slate-800 rounded-xl border border-indigo-100 dark:border-indigo-800 overflow-hidden">
    <div class="px-5 py-3 border-b border-indigo-100 dark:border-indigo-800 bg-indigo-50/70 dark:bg-indigo-950/50">
      <h2 class="text-sm font-semibold text-indigo-700 dark:text-indigo-300">行动摘要</h2>
    </div>

    <div class="p-5 space-y-4">
      <div>
        <p class="text-xs font-medium text-slate-400 dark:text-slate-500 mb-1">核心结论</p>
        <p class="text-base leading-relaxed text-slate-800 dark:text-slate-200">{{ summary.conclusion }}</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div class="rounded-lg bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-100 dark:border-emerald-800 p-3">
          <p class="text-xs font-medium text-emerald-600 dark:text-emerald-400 mb-1">先做这件事</p>
          <p class="text-sm leading-relaxed text-emerald-900 dark:text-emerald-200">{{ summary.first_action }}</p>
        </div>

        <div class="rounded-lg bg-sky-50 dark:bg-sky-950/50 border border-sky-100 dark:border-sky-800 p-3">
          <p class="text-xs font-medium text-sky-600 dark:text-sky-400 mb-1">预计周期</p>
          <p class="text-sm leading-relaxed text-sky-900 dark:text-sky-200">{{ summary.timeframe }}</p>
        </div>

        <div class="rounded-lg bg-amber-50 dark:bg-amber-950/50 border border-amber-100 dark:border-amber-800 p-3">
          <p class="text-xs font-medium text-amber-600 dark:text-amber-400 mb-1">主要风险</p>
          <p class="text-sm leading-relaxed text-amber-900 dark:text-amber-200">{{ summary.risk }}</p>
        </div>

        <div class="rounded-lg bg-violet-50 dark:bg-violet-950/50 border border-violet-100 dark:border-violet-800 p-3">
          <p class="text-xs font-medium text-violet-600 dark:text-violet-400 mb-1">适合场景</p>
          <p class="text-sm leading-relaxed text-violet-900 dark:text-violet-200">{{ summary.fit_for }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
