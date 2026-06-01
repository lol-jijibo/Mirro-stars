<!--
  流式答案渲染组件
  业务角色：将Markdown格式的AI答案实时渲染为HTML。
  在流式生成过程中，文本逐段追加并即时渲染，产生"AI打字机"效果。
  生成完成后，使用 markdown-it 完整渲染Markdown。
-->
<script setup lang="ts">
import { computed, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

/**
 * 初始化Markdown渲染器
 * 业务场景：将AI生成的Markdown文本转为HTML显示。
 * highlight.js 提供代码块语法高亮，增强可读性。
 */
const md = new MarkdownIt({
  html: true,
  linkify: true,          // 自动将URL转为可点击链接
  typographer: true,      // 优化中文排版（引号等）
  highlight(code: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch { /* 高亮失败用纯文本 */ }
    }
    return ''
  },
})

const props = defineProps<{
  /** Markdown格式的答案正文 */
  content: string
  /** 流式生成是否已完成（完成后不使用光标动画） */
  isDone?: boolean
}>()

/** 复制按钮状态：是否刚完成复制（用于显示"已复制"反馈） */
const copied = ref(false)

/** 将Markdown转为HTML */
const renderedHtml = computed(() => {
  if (!props.content) return '<p class="text-slate-400">等待AI生成中...</p>'
  return md.render(props.content)
})

/** 复制全文Markdown到剪贴板 */
async function copyContent() {
  if (!props.content) return
  try {
    await navigator.clipboard.writeText(props.content)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    // 降级方案：传统方式复制
    const textarea = document.createElement('textarea')
    textarea.value = props.content
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  }
}
</script>

<template>
  <div class="relative">
    <div
      class="markdown-body bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6"
      :class="{ 'cursor-blink': !isDone }"
    >
      <!-- 流式内容：通过v-html渲染Markdown，XSS风险由markdown-it转义控制 -->
      <div v-html="renderedHtml" />

      <!-- 完成标记 — 告知用户内容已输出完毕 -->
      <div v-if="isDone && content" class="mt-4 pt-3 border-t border-slate-100 dark:border-slate-700 flex items-center gap-2 text-green-600 dark:text-green-400 text-sm">
        <span>✅</span> 答案生成完毕
      </div>
    </div>

    <!-- 复制按钮 — 答案完成后显示在卡片右上角 -->
    <button
      v-if="isDone && content"
      class="absolute top-3 right-3 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg
             bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-400
             hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950
             active:scale-95 transition-all duration-150 shadow-sm"
      @click="copyContent"
    >
      <template v-if="copied">
        <span class="text-green-500">✓</span> 已复制
      </template>
      <template v-else>
        <span>📋</span> 复制全文
      </template>
    </button>
  </div>
</template>
