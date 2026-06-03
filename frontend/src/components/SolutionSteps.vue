<!--
  执行清单组件
  业务角色：将AI生成的解决步骤转成可跟进的任务清单。
  用户可以标记状态、记录备注，并在同一问题下自动保存执行进度。
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { SolutionStep } from '@/types'

type StepStatus = 'todo' | 'doing' | 'done' | 'paused'

interface StepState {
  status: StepStatus
  note: string
}

const props = defineProps<{
  /** 分步执行计划列表 */
  steps: SolutionStep[]
  /** 本地保存执行状态的键，通常使用question_id */
  storageKey?: string
  /** 只读展示模式，用于分享页 */
  readonly?: boolean
}>()

/** 每一步的执行状态 */
const stepStates = ref<Record<number, StepState>>({})

/** 状态选项 */
const statusOptions: { value: StepStatus; label: string }[] = [
  { value: 'todo', label: '待做' },
  { value: 'doing', label: '进行中' },
  { value: 'done', label: '已完成' },
  { value: 'paused', label: '暂缓' },
]

/** 当前清单本地保存键 */
const localKey = computed(() => props.storageKey ? `mirro-checklist-${props.storageKey}` : '')

/** 已完成步骤数量 */
const doneCount = computed(() =>
  props.steps.filter(step => getStepState(step.step).status === 'done').length
)

/** 完成百分比 */
const progressPercent = computed(() => {
  if (props.steps.length === 0) return 0
  return Math.round(doneCount.value / props.steps.length * 100)
})

/** 获取某一步的状态，缺省为待做 */
function getStepState(step: number): StepState {
  return stepStates.value[step] || { status: 'todo', note: '' }
}

/** 修改步骤状态 */
function setStatus(step: number, status: StepStatus) {
  if (props.readonly) return
  const current = getStepState(step)
  stepStates.value = {
    ...stepStates.value,
    [step]: { ...current, status },
  }
}

/** 修改步骤备注 */
function setNote(step: number, note: string) {
  if (props.readonly) return
  const current = getStepState(step)
  stepStates.value = {
    ...stepStates.value,
    [step]: { ...current, note },
  }
}

/** 初始化或读取本地保存的执行状态 */
function loadStates() {
  let saved: Record<number, StepState> = {}
  if (localKey.value) {
    try {
      saved = JSON.parse(localStorage.getItem(localKey.value) || '{}')
    } catch {
      saved = {}
    }
  }

  const next: Record<number, StepState> = {}
  for (const step of props.steps) {
    const current = saved[step.step]
    next[step.step] = {
      status: current?.status || 'todo',
      note: current?.note || '',
    }
  }
  stepStates.value = next
}

/** 保存执行状态到本地 */
function saveStates() {
  if (!localKey.value || props.readonly) return
  localStorage.setItem(localKey.value, JSON.stringify(stepStates.value))
}

/** 状态按钮样式 */
function statusClass(step: number, status: StepStatus) {
  const active = getStepState(step).status === status
  if (active && status === 'done') return 'bg-emerald-500 text-white shadow-sm shadow-emerald-500/25'
  if (active && status === 'doing') return 'bg-indigo-500 text-white shadow-sm shadow-indigo-500/25'
  if (active && status === 'paused') return 'bg-amber-500 text-white shadow-sm shadow-amber-500/25'
  if (active) return 'bg-slate-600 text-white shadow-sm'
  return 'bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600'
}

watch(
  () => [props.steps, props.storageKey],
  loadStates,
  { immediate: true, deep: true }
)

watch(stepStates, saveStates, { deep: true })
</script>

<template>
  <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
    <!-- 标题栏 -->
    <div class="px-5 py-4 border-b border-slate-100 dark:border-slate-700 bg-emerald-50/50 dark:bg-emerald-950/40">
      <div class="flex items-center justify-between gap-4">
        <div>
          <h3 class="font-semibold text-sm text-emerald-700 dark:text-emerald-300">
            共 {{ steps.length }} 步
          </h3>
          <p v-if="!readonly" class="mt-1 text-xs text-emerald-600/80 dark:text-emerald-400/80">
            已完成 {{ doneCount }} 步，进度 {{ progressPercent }}%
          </p>
        </div>
        <div v-if="!readonly" class="w-28 h-2 rounded-full bg-white dark:bg-slate-700 overflow-hidden border border-emerald-100 dark:border-emerald-800">
          <div
            class="h-full bg-emerald-500 transition-all duration-300"
            :style="{ width: `${progressPercent}%` }"
          />
        </div>
      </div>
    </div>

    <!-- 步骤时间轴 -->
    <div class="p-5">
      <div v-if="steps.length === 0" class="text-center py-4 text-slate-400 dark:text-slate-500 text-sm">
        等待执行计划生成中...
      </div>

      <div v-else class="relative">
        <div class="absolute left-5 top-0 bottom-0 w-0.5 bg-emerald-200 dark:bg-emerald-800" />

        <div
          v-for="s in steps"
          :key="s.step"
          class="relative pl-12 pb-5 last:pb-0"
        >
          <div
            class="absolute left-3.5 w-3 h-3 rounded-full ring-4 z-10"
            :class="getStepState(s.step).status === 'done'
              ? 'bg-emerald-500 ring-emerald-100 dark:ring-emerald-900'
              : getStepState(s.step).status === 'doing'
                ? 'bg-indigo-500 ring-indigo-100 dark:ring-indigo-900'
                : getStepState(s.step).status === 'paused'
                  ? 'bg-amber-500 ring-amber-100 dark:ring-amber-900'
                  : 'bg-slate-300 dark:bg-slate-600 ring-slate-100 dark:ring-slate-800'"
          />

          <div class="bg-slate-50 dark:bg-slate-900/60 rounded-lg p-4 border border-slate-100 dark:border-slate-700 transition-colors">
            <div class="flex flex-col gap-3">
              <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                <div>
                  <h4 class="font-semibold text-slate-800 dark:text-slate-200 leading-snug">
                    第{{ s.step }}步：{{ s.title }}
                  </h4>
                  <p class="mt-1 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">{{ s.description }}</p>
                </div>
                <span class="inline-flex self-start text-xs text-emerald-600 dark:text-emerald-300 bg-emerald-100 dark:bg-emerald-950 px-2 py-0.5 rounded-full font-medium whitespace-nowrap">
                  {{ s.duration }}
                </span>
              </div>

              <div v-if="!readonly" class="flex flex-wrap gap-1.5">
                <button
                  v-for="option in statusOptions"
                  :key="option.value"
                  class="px-2.5 py-1 rounded-md text-xs font-medium transition-all active:scale-95"
                  :class="statusClass(s.step, option.value)"
                  @click="setStatus(s.step, option.value)"
                >
                  {{ option.label }}
                </button>
              </div>

              <textarea
                v-if="!readonly"
                :value="getStepState(s.step).note"
                rows="2"
                maxlength="300"
                placeholder="记录执行卡点、下一步或复盘想法..."
                class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg resize-none
                       text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500
                       focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:focus:ring-emerald-400"
                @input="setNote(s.step, ($event.target as HTMLTextAreaElement).value)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
