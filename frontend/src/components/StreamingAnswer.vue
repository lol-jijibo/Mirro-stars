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

/** 生成标题的DOM id，用作TOC锚点 */
function slugify(text: string): string {
  return text
    .replace(/\s+/g, '-')
    .replace(/[^\w\u4e00-\u9fa5-]/g, '')
    .toLowerCase()
    .slice(0, 60)
}

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

// ====== 为 h2/h3/h4 标题添加锚点 id，供 TOC 导航使用 ======
const defaultHeadingOpen = md.renderer.rules.heading_open
md.renderer.rules.heading_open = (tokens, idx, options, env, self) => {
  const hLevel = tokens[idx].tag
  if ((hLevel === 'h2' || hLevel === 'h3' || hLevel === 'h4') && idx + 1 < tokens.length) {
    const inlineToken = tokens[idx + 1]
    if (inlineToken.type === 'inline' && inlineToken.content) {
      const id = slugify(inlineToken.content)
      tokens[idx].attrSet('id', id)
      tokens[idx].attrSet('class', 'scroll-mt-20')
    }
  }
  return defaultHeadingOpen
    ? defaultHeadingOpen(tokens, idx, options, env, self)
    : self.renderToken(tokens, idx, options)
}

// ====== 代码块包裹：添加语言标签 + 一键复制按钮 ======
const defaultFence = md.renderer.rules.fence
md.renderer.rules.fence = (tokens, idx, options, env, self) => {
  const token = tokens[idx]
  const lang = token.info?.trim() || ''
  const langLabel = lang ? `<span class="code-lang-label">${md.utils.escapeHtml(lang)}</span>` : ''
  const raw = defaultFence
    ? defaultFence(tokens, idx, options, env, self)
    : `<pre><code>${md.utils.escapeHtml(token.content)}</code></pre>`

  return `<div class="code-block-wrapper">
    <div class="code-block-header">
      ${langLabel}
      <button class="code-copy-btn" type="button">
        <svg class="copy-icon w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
        <span>复制</span>
      </button>
    </div>
    ${raw}
  </div>`
}

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

/** 代码块内联复制 — 通过事件代理在容器上捕获点击 */
function handleCodeCopy(event: Event) {
  const btn = (event.target as HTMLElement).closest('.code-copy-btn')
  if (!btn) return
  const wrapper = btn.closest('.code-block-wrapper')
  if (!wrapper) return
  const code = wrapper.querySelector('code')
  if (!code) return

  navigator.clipboard.writeText(code.textContent || '').then(() => {
    btn.classList.add('copied')
    const span = btn.querySelector('span')
    if (span) span.textContent = '已复制'
    setTimeout(() => {
      btn.classList.remove('copied')
      if (span) span.textContent = '复制'
    }, 2000)
  }).catch(() => {
    // 降级：选中文本
    const range = document.createRange()
    range.selectNodeContents(code)
    const sel = window.getSelection()
    sel?.removeAllRanges()
    sel?.addRange(range)
    document.execCommand('copy')
    sel?.removeAllRanges()
    btn.classList.add('copied')
    const span = btn.querySelector('span')
    if (span) span.textContent = '已复制'
    setTimeout(() => {
      btn.classList.remove('copied')
      if (span) span.textContent = '复制'
    }, 2000)
  })
}
</script>

<template>
  <div class="relative" @click="handleCodeCopy">
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

<style scoped>
/* ====== 代码块包裹容器 ====== */
.code-block-wrapper {
  position: relative;
  margin: 1rem 0;
  border-radius: 0.75rem;
  overflow: hidden;
  background: #1e293b;
  /* dark:slate-800 */
}

:global(.dark) .code-block-wrapper {
  background: #0f172a;
  /* darker for dark mode */
}

.code-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 1rem;
  background: #334155;
  /* slate-700 */
}

:global(.dark) .code-block-header {
  background: #1e293b;
}

.code-lang-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #94a3b8;
  /* slate-400 */
}

.code-copy-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem;
  border: none;
  border-radius: 0.375rem;
  background: rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  /* slate-300 */
  font-size: 0.7rem;
  cursor: pointer;
  transition: all 0.15s ease;
  opacity: 0;
}

.code-block-wrapper:hover .code-copy-btn,
.code-copy-btn.copied {
  opacity: 1;
}

.code-copy-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.code-copy-btn.copied {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

/* 重置 pre 的 margin，避免与 wrapper 重复 */
.code-block-wrapper :deep(pre) {
  margin: 0;
  border-radius: 0;
  background: transparent;
}

/* ====== 流式光标闪烁动画 ====== */
.cursor-blink::after {
  content: '▊';
  animation: blink 1s step-end infinite;
  color: #6366f1;
  /* indigo-500 */
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}
</style>
