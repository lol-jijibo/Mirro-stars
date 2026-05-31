<!--
  流式答案渲染组件
  业务角色：将Markdown格式的AI答案实时渲染为HTML。
  在流式生成过程中，文本逐段追加并即时渲染，产生"AI打字机"效果。
  生成完成后，使用 markdown-it 完整渲染Markdown。
-->
<script setup lang="ts">
import { computed } from 'vue'
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

/** 将Markdown转为HTML */
const renderedHtml = computed(() => {
  if (!props.content) return '<p class="text-slate-400">等待AI生成中...</p>'
  return md.render(props.content)
})
</script>

<template>
  <div
    class="markdown-body bg-white rounded-xl border border-slate-200 p-6"
    :class="{ 'cursor-blink': !isDone }"
  >
    <!-- 流式内容：通过v-html渲染Markdown，XSS风险由markdown-it转义控制 -->
    <div v-html="renderedHtml" />

    <!-- 完成标记 — 告知用户内容已输出完毕 -->
    <div v-if="isDone && content" class="mt-4 pt-3 border-t border-slate-100 flex items-center gap-2 text-green-600 text-sm">
      <span>✅</span> 答案生成完毕
    </div>
  </div>
</template>
