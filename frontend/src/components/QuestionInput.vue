<!--
  问题输入组件 — 用户提交问题的交互入口
  业务角色：首页的核心交互组件，用户在此输入问题并提交。
  支持回车快捷提交、字数提示、加载状态禁用等细节。
-->
<script setup lang="ts">
import { ref, computed } from 'vue'

const emit = defineEmits<{
  /** 用户提交问题时触发，携带输入内容 */
  submit: [content: string]
}>()

const props = defineProps<{
  /** 是否正在加载中（AI生成答案期间禁用输入） */
  loading?: boolean
}>()

/** 用户输入的提问内容 */
const inputContent = ref('')

/** 还能输入多少字（最多500字） */
const remainingChars = computed(() => 500 - inputContent.value.length)

/** 是否达到字数上限 */
const isOverLimit = computed(() => inputContent.value.length > 500)

/** 是否可以提交：不少于5字、不超过500字、不在加载中 */
const canSubmit = computed(() =>
  inputContent.value.trim().length >= 5 && !isOverLimit.value && !props.loading
)

/** 提交问题 — 校验通过后向父组件发送事件 */
function handleSubmit() {
  if (!canSubmit.value) return
  emit('submit', inputContent.value.trim())
}

/** 处理键盘快捷键 */
function handleKeydown(e: KeyboardEvent) {
  // Enter（非Shift）或 Ctrl+Enter → 提交
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSubmit()
  }
}
</script>

<template>
  <div class="w-full">
    <!-- 输入区域 -->
    <div class="relative">
      <textarea
        v-model="inputContent"
        :disabled="loading"
        placeholder="输入你遇到的问题…&#10;例如：我25岁想转行做程序员，零基础该怎么规划？"
        rows="3"
        class="w-full px-4 py-3 text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-xl resize-none
               placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 focus:border-transparent
               disabled:bg-slate-100 dark:disabled:bg-slate-700 disabled:cursor-not-allowed transition-all text-base"
        :class="{ 'border-red-400 dark:border-red-500 focus:ring-red-500': isOverLimit }"
        @keydown="handleKeydown"
      />

      <!-- 底部操作栏：字数统计 + 提交按钮 -->
      <div class="flex items-center justify-between mt-2">
        <span
          class="text-xs"
          :class="isOverLimit ? 'text-red-500 dark:text-red-400' : remainingChars <= 50 ? 'text-amber-500 dark:text-amber-400' : 'text-slate-400 dark:text-slate-500'"
        >
          {{ isOverLimit ? `超出 ${Math.abs(remainingChars)} 字` : `还可输入 ${remainingChars} 字` }}
        </span>

        <button
          :disabled="!canSubmit"
          class="px-5 py-2 bg-indigo-600 dark:bg-indigo-500 text-white text-sm font-medium rounded-lg
                 hover:bg-indigo-700 dark:hover:bg-indigo-600 active:scale-95
                 disabled:bg-slate-300 dark:disabled:bg-slate-700 disabled:cursor-not-allowed disabled:active:scale-100
                 transition-all duration-150"
          @click="handleSubmit"
        >
          <!-- 加载中显示旋转动画 -->
          <span v-if="loading" class="flex items-center gap-2">
            <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            分析中…
          </span>
          <span v-else>🔍 求解</span>
        </button>
      </div>
    </div>

    <!-- 提示文字 -->
    <p class="mt-3 text-xs text-slate-400 dark:text-slate-500 text-center">
      按 <kbd class="px-1 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px] font-mono">Enter</kbd> / <kbd class="px-1 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px] font-mono">Ctrl+Enter</kbd> 提交，
      <kbd class="px-1 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px] font-mono">Shift+Enter</kbd> 换行 ·
      <kbd class="px-1 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px] font-mono">Esc</kbd> 取消生成
    </p>
  </div>
</template>
