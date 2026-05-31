<!--
  流程图查看器组件
  业务角色：将Mermaid流程图语法渲染为可视化图形。
  用户通过流程图直观看到从"当前问题"到"解决方案"的路径，增强理解。
-->
<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import mermaid from 'mermaid'

/**
 * 初始化Mermaid配置
 * 业务场景：配置Mermaid的主题和渲染参数，使其与Mirro品牌色一致。
 */
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  themeVariables: {
    primaryColor: '#eef2ff',      // 节点背景：浅靛蓝
    primaryBorderColor: '#6366f1', // 节点边框：品牌主色
    lineColor: '#a5b4fc',          // 连接线：柔和靛蓝
    fontSize: '14px',
  },
})

const props = defineProps<{
  /** Mermaid流程图语法字符串 */
  mermaidText: string
}>()

const containerRef = ref<HTMLDivElement>()
const svgContent = ref('')
const hasError = ref(false)

/**
 * 渲染Mermaid流程图
 * 业务逻辑：监听mermaidText变化，当AI返回流程图语法后自动渲染为SVG图形。
 */
async function renderChart() {
  if (!props.mermaidText || !containerRef.value) return

  try {
    // 生成唯一ID避免多图冲突
    const id = `mermaid-${Math.random().toString(36).slice(2, 8)}`
    const { svg } = await mermaid.render(id, props.mermaidText)
    svgContent.value = svg
    hasError.value = false
  } catch {
    // 渲染失败时显示提示
    hasError.value = true
  }
}

// 监听props变化重新渲染
watch(() => props.mermaidText, () => {
  nextTick(renderChart)
})

onMounted(() => {
  nextTick(renderChart)
})
</script>

<template>
  <div class="bg-white rounded-xl border border-slate-200 overflow-hidden">
    <!-- 标题栏 -->
    <div class="px-5 py-3 border-b border-slate-100 bg-indigo-50/50">
      <h3 class="font-semibold text-sm text-indigo-700">📊 流程可视化</h3>
    </div>

    <!-- Mermaid渲染区域 -->
    <div class="p-4">
      <div v-if="hasError" class="text-center py-8 text-slate-400">
        <p>⚠️ 流程图解析失败，请尝试刷新</p>
        <pre class="mt-2 text-xs text-left bg-slate-50 p-3 rounded overflow-x-auto">{{ mermaidText }}</pre>
      </div>
      <div v-else-if="mermaidText" class="mermaid-container" v-html="svgContent" ref="containerRef" />
      <div v-else class="text-center py-8 text-slate-400">
        等待流程图生成中...
      </div>
    </div>
  </div>
</template>
