<!--
  搜索来源列表组件
  业务角色：展示AI从全网搜索到的参考资料和案例链接。
  每条来源包含标题、URL链接和内容摘要，增强答案的可信度。
-->
<script setup lang="ts">
import type { Source } from '@/types'

defineProps<{
  /** 搜索来源列表 */
  sources: Source[]
}>()
</script>

<template>
  <div class="bg-white rounded-xl border border-slate-200 overflow-hidden">
    <!-- 标题栏 -->
    <div class="px-5 py-3 border-b border-slate-100 bg-amber-50/50">
      <h3 class="font-semibold text-sm text-amber-700">📎 共 {{ sources.length }} 条参考来源</h3>
    </div>

    <!-- 来源列表 -->
    <div class="p-4 space-y-3">
      <div v-if="sources.length === 0" class="text-center py-4 text-slate-400 text-sm">
        暂无搜索来源
      </div>

      <a
        v-for="(source, idx) in sources"
        :key="idx"
        :href="source.url"
        target="_blank"
        rel="noopener noreferrer"
        class="block p-3 rounded-lg border border-slate-100 hover:bg-indigo-50 hover:border-indigo-200 transition-colors group"
      >
        <div class="flex items-start gap-2">
          <span class="text-slate-400 mt-0.5 flex-shrink-0">🔗</span>
          <div class="min-w-0">
            <h4 class="text-sm font-medium text-indigo-600 group-hover:text-indigo-700 truncate">
              {{ source.title }}
            </h4>
            <p class="text-xs text-slate-500 mt-0.5 line-clamp-2">{{ source.snippet }}</p>
          </div>
        </div>
      </a>
    </div>
  </div>
</template>
