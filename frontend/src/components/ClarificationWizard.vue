<!--
  提问澄清向导
  业务角色：在正式生成答案前收集用户现状、目标和限制条件。
  这些补充信息只作为AI上下文使用，不覆盖用户原始提问。
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

const emit = defineEmits<{
  /** 携带补充上下文继续生成 */
  confirm: [context: string]
  /** 不补充信息，直接生成 */
  skip: []
  /** 取消本次澄清 */
  cancel: []
}>()

defineProps<{
  /** 用户原始提问 */
  question: string
}>()

/** 当前背景 */
const background = ref('')
/** 目标结果 */
const goal = ref('')
/** 限制条件 */
const constraints = ref('')

/** 是否填写了至少一项补充信息 */
const hasAnyContext = computed(() =>
  [background.value, goal.value, constraints.value].some(item => item.trim().length > 0)
)

/** 汇总澄清上下文 */
function buildContext() {
  const parts = [
    background.value.trim() ? `当前现状：${background.value.trim()}` : '',
    goal.value.trim() ? `期望结果：${goal.value.trim()}` : '',
    constraints.value.trim() ? `限制条件：${constraints.value.trim()}` : '',
  ].filter(Boolean)
  return parts.join('\n')
}

/** 确认补充并继续 */
function handleConfirm() {
  emit('confirm', buildContext())
}
</script>

<template>
  <div class="mt-5 bg-white dark:bg-slate-800 border border-indigo-100 dark:border-indigo-800 rounded-xl overflow-hidden shadow-sm">
    <div class="px-5 py-4 bg-indigo-50/70 dark:bg-indigo-950/50 border-b border-indigo-100 dark:border-indigo-800">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-sm font-semibold text-indigo-700 dark:text-indigo-300">先补充一点背景，答案会更贴近你</h2>
          <p class="mt-1 text-xs text-indigo-500 dark:text-indigo-400 line-clamp-2">{{ question }}</p>
        </div>
        <button
          class="text-xs text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
          @click="emit('cancel')"
        >
          关闭
        </button>
      </div>
    </div>

    <div class="p-5 space-y-4">
      <label class="block">
        <span class="text-xs font-medium text-slate-500 dark:text-slate-400">你的现状</span>
        <textarea
          v-model="background"
          rows="2"
          maxlength="260"
          placeholder="例如：目前是运营，零编程基础；或最近和伴侣沟通很频繁但总吵架"
          class="mt-1 w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg resize-none
                 text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500
                 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400"
        />
      </label>

      <label class="block">
        <span class="text-xs font-medium text-slate-500 dark:text-slate-400">想要的结果</span>
        <textarea
          v-model="goal"
          rows="2"
          maxlength="240"
          placeholder="例如：3个月内确认方向；或希望关系稳定下来、减少内耗"
          class="mt-1 w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg resize-none
                 text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500
                 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400"
        />
      </label>

      <label class="block">
        <span class="text-xs font-medium text-slate-500 dark:text-slate-400">时间、预算或其他限制</span>
        <textarea
          v-model="constraints"
          rows="2"
          maxlength="240"
          placeholder="例如：每天只有1小时；预算很少；不能换城市；不想冒太大风险"
          class="mt-1 w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg resize-none
                 text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500
                 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400"
        />
      </label>

      <div class="flex items-center justify-end gap-2 pt-1">
        <button
          class="px-4 py-2 text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
          @click="emit('skip')"
        >
          直接生成
        </button>
        <button
          class="px-5 py-2 text-sm font-medium rounded-lg text-white bg-indigo-600 dark:bg-indigo-500
                 hover:bg-indigo-700 dark:hover:bg-indigo-600 active:scale-95 disabled:bg-slate-300 dark:disabled:bg-slate-700
                 disabled:cursor-not-allowed disabled:active:scale-100 transition-all"
          :disabled="!hasAnyContext"
          @click="handleConfirm"
        >
          带补充生成
        </button>
      </div>
    </div>
  </div>
</template>
