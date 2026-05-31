import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

/**
 * Vite 构建配置
 * - @vitejs/plugin-vue: Vue3 SFC 编译
 * - @tailwindcss/vite: Tailwind CSS v4 集成
 * - resolve.alias: @ 路径别名 → src 目录
 */
export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    // 代理API请求到后端FastAPI服务（解决前后端分离的跨域问题）
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
