/**
 * Mirro 前端应用入口
 * 负责组装Vue应用：挂载路由、状态管理、全局样式。
 * 业务场景：用户访问网站时，从这里初始化整个SPA。
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

const app = createApp(App)

// Pinia 状态管理 — 管理流式答案生成等全局状态
app.use(createPinia())
// Vue Router — 管理页面路由导航
app.use(router)

app.mount('#app')
