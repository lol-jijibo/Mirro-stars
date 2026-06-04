<!--
  真实案例外链列表组件
  用于展示第三方平台的公开案例入口，引导用户跳转原平台查看完整内容。
  仅呈现摘要、来源和跳转链接，避免在站内搬运第三方正文或视频资源。
-->
<script setup lang="ts">
import { ref } from 'vue'

type CasePlatform = 'douyin' | 'xiaohongshu' | 'zhihu' | 'juejin' | 'bilibili' | 'web'

interface ExternalCase {
  id: string
  platform: CasePlatform
  title: string
  summary: string
  sourceType: '视频' | '帖子' | '回答' | '文章'
  matchLevel: '高' | '中' | '低'
  buildUrl: (query: string) => string
}

const props = defineProps<{
  question: string
}>()

const failedLogos = ref<Partial<Record<CasePlatform, boolean>>>({})

const cases: ExternalCase[] = [
  {
    id: 'douyin-case',
    platform: 'douyin',
    title: '抖音亲历视频',
    summary: '优先寻找第一人称讲述、评论补充和完整处理过程的视频内容。',
    sourceType: '视频',
    matchLevel: '高',
    buildUrl: (query) => `https://www.douyin.com/search/${encodeURIComponent(query)}`,
  },
  {
    id: 'xiaohongshu-case',
    platform: 'xiaohongshu',
    title: '小红书经验帖',
    summary: '适合查看个人记录、复盘过程、避坑经验和评论区里的相似经历。',
    sourceType: '帖子',
    matchLevel: '中',
    buildUrl: (query) => `https://www.xiaohongshu.com/search_result?keyword=${encodeURIComponent(query)}`,
  },
  {
    id: 'zhihu-case',
    platform: 'zhihu',
    title: '知乎相关回答',
    summary: '适合查看长文本案例、背景补充和不同用户的处理方式。',
    sourceType: '回答',
    matchLevel: '高',
    buildUrl: (query) => `https://www.zhihu.com/search?type=content&q=${encodeURIComponent(query)}`,
  },
  {
    id: 'juejin-case',
    platform: 'juejin',
    title: '掘金实践文章',
    summary: '偏技术类问题可优先查看真实排查过程、踩坑记录和解决方案。',
    sourceType: '文章',
    matchLevel: '中',
    buildUrl: (query) => `https://juejin.cn/search?query=${encodeURIComponent(query)}`,
  },
  {
    id: 'bilibili-case',
    platform: 'bilibili',
    title: 'B站案例视频',
    summary: '适合检索过程讲解、经验复盘、测评记录和弹幕评论里的补充视角。',
    sourceType: '视频',
    matchLevel: '中',
    buildUrl: (query) => `https://search.bilibili.com/all?keyword=${encodeURIComponent(query)}`,
  },
  {
    id: 'web-case',
    platform: 'web',
    title: '全网公开链接',
    summary: '从搜索引擎聚合公开网页，适合发现论坛、博客和平台索引页。',
    sourceType: '文章',
    matchLevel: '中',
    buildUrl: (query) => `https://www.bing.com/search?q=${encodeURIComponent(query)}`,
  },
]

const platformMeta: Record<CasePlatform, { label: string; mark: string; tone: string; logoUrl?: string }> = {
  douyin: {
    label: '抖音',
    mark: '抖',
    tone: 'bg-black',
    logoUrl: 'https://lf1-cdn-tos.bytegoofy.com/goofy/ies/douyin_web/public/favicon.ico',
  },
  xiaohongshu: {
    label: '小红书',
    mark: '红',
    tone: 'bg-red-50 dark:bg-red-950',
    logoUrl: 'https://www.xiaohongshu.com/favicon.ico',
  },
  zhihu: {
    label: '知乎',
    mark: '知',
    tone: 'bg-blue-50 dark:bg-blue-950',
    logoUrl: 'https://static.zhihu.com/heifetz/favicon.ico',
  },
  juejin: {
    label: '掘金',
    mark: '掘',
    tone: 'bg-cyan-50 dark:bg-cyan-950',
    logoUrl: 'https://lf3-cdn-tos.bytescm.com/obj/static/xitu_juejin_web/static/favicons/favicon-32x32.png',
  },
  bilibili: {
    label: 'B站',
    mark: 'B',
    tone: 'bg-pink-50 dark:bg-pink-950',
    logoUrl: 'https://www.bilibili.com/favicon.ico',
  },
  web: { label: '网页', mark: '链', tone: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300' },
}

function getPlatformMeta(platform: CasePlatform) {
  return platformMeta[platform]
}

function buildCaseQuery(platform: CasePlatform) {
  const keyword = props.question.trim() || '真实经历'
  if (platform === 'juejin') return `${keyword} 踩坑 解决`
  if (platform === 'web') return `${keyword} 亲身经历 OR 真实案例`
  return `${keyword} 亲身经历 真实案例`
}

function buildCaseUrl(item: ExternalCase) {
  return item.buildUrl(buildCaseQuery(item.platform))
}

function buildGlobalSearchUrl() {
  const query = `${props.question.trim() || '真实经历'} 抖音 小红书 知乎 B站 真实案例`
  return `https://www.bing.com/search?q=${encodeURIComponent(query)}`
}

function markLogoFailed(platform: CasePlatform) {
  failedLogos.value[platform] = true
}
</script>

<template>
  <aside class="space-y-3">
    <div class="flex items-start justify-between gap-3">
      <div>
        <p class="text-xs font-medium text-indigo-500 dark:text-indigo-300">真实案例</p>
        <h2 class="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">站外亲历链接</h2>
      </div>
      <span class="rounded-full border border-slate-200 px-2 py-1 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
        {{ cases.length }} 条
      </span>
    </div>

    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
      <a
        v-for="item in cases"
        :key="item.id"
        :href="buildCaseUrl(item)"
        target="_blank"
        rel="noopener noreferrer"
        class="group block rounded-lg border border-slate-200 bg-white p-4 transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-md dark:border-slate-700 dark:bg-slate-800 dark:hover:border-indigo-500"
      >
        <div class="flex items-center justify-between gap-3">
          <div class="flex min-w-0 items-center gap-2">
            <span
              class="flex h-7 w-7 flex-shrink-0 items-center justify-center overflow-hidden rounded-md text-xs font-bold"
              :class="getPlatformMeta(item.platform).tone"
            >
              <img
                v-if="getPlatformMeta(item.platform).logoUrl && !failedLogos[item.platform]"
                :src="getPlatformMeta(item.platform).logoUrl"
                :alt="`${getPlatformMeta(item.platform).label} logo`"
                class="h-full w-full object-cover"
                loading="lazy"
                @error="markLogoFailed(item.platform)"
              >
              <span v-else>
                {{ getPlatformMeta(item.platform).mark }}
              </span>
            </span>
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold text-slate-800 group-hover:text-indigo-600 dark:text-slate-100 dark:group-hover:text-indigo-300">
                {{ item.title }}
              </p>
              <p class="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
                {{ getPlatformMeta(item.platform).label }} · {{ item.sourceType }} · 匹配{{ item.matchLevel }}
              </p>
            </div>
          </div>
          <span class="flex-shrink-0 text-sm text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-indigo-400">
            →
          </span>
        </div>
        <p class="mt-3 line-clamp-3 text-sm leading-6 text-slate-500 dark:text-slate-400">
          {{ item.summary }}
        </p>
      </a>
    </div>

    <a
      :href="buildGlobalSearchUrl()"
      target="_blank"
      rel="noopener noreferrer"
      class="w-full rounded-lg border border-dashed border-slate-300 px-3 py-2.5 text-sm font-medium text-slate-500 transition hover:border-indigo-300 hover:text-indigo-600 dark:border-slate-700 dark:text-slate-400 dark:hover:border-indigo-500 dark:hover:text-indigo-300"
    >
      打开全网检索
    </a>
  </aside>
</template>
