/**
 * Vue Router 路由配置
 * 定义前端页面路由映射。
 * 业务场景：Mirro 有4个主要页面 — 首页提问、答案详情、历史列表、统计看板
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

/**
 * 路由表定义
 * / → 首页（提问入口 + 功能介绍）
 * /question/:id → 答案详情页（流式AI答案 + 流程图 + 步骤 + 来源）
 * /history → 问题历史列表
 * /dashboard → 问题统计看板
 */
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: 'Mirro — AI 问题解决引擎' },
  },
  {
    path: '/question/:id',
    name: 'question',
    component: () => import('@/views/QuestionView.vue'),
    meta: { title: '解答详情' },
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('@/views/HistoryView.vue'),
    meta: { title: '问题历史' },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: '统计看板' },
  },
  {
    path: '/share/:answerId',
    name: 'share',
    component: () => import('@/views/ShareView.vue'),
    meta: { title: '分享答案 — Mirro' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    // 每次路由切换滚动到顶部，提升浏览体验
    return { top: 0 }
  },
})

// 全局路由守卫：动态更新页面标题
router.afterEach((to) => {
  document.title = (to.meta.title as string) || 'Mirro'
})

export default router
