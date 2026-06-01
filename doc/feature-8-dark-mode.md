# Feature 8: 深色模式

## 需求背景

深色模式是现代 Web 应用的标准功能，能减少夜间使用时对眼睛的刺激，同时降低 OLED 屏幕功耗。README TODO 中列有此功能需求。

## 业务逻辑

### 用户操作流程

1. 用户首次访问 → 自动检测系统主题偏好
2. 点击导航栏右侧的 ☀️/🌙 按钮手动切换
3. 手动切换后偏好保存到 localStorage
4. 下次访问时优先使用 localStorage 中的偏好
5. 如果从未手动设置，则继续跟随系统主题

### 技术方案

**Tailwind CSS v4 的 dark: 变体机制：**

```css
/* main.css */
@import "tailwindcss";
@custom-variant dark (&:where(.dark, .dark *));
```

这行 CSS 告诉 Tailwind：当 HTML 元素上有 `.dark` 类时，所有 `dark:` 前缀的样式生效。

### 暗色模式管理逻辑

**文件:** [frontend/src/App.vue](../../frontend/src/App.vue)

#### 状态管理

```typescript
const isDark = ref(false)

// 优先级：localStorage > 系统偏好 > 默认关闭
function initDarkMode() {
  const stored = localStorage.getItem('mirro-dark-mode')
  if (stored === 'dark') {
    isDark.value = true
  } else if (stored === 'light') {
    isDark.value = false
  } else {
    isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }
  applyDarkMode()
}

function applyDarkMode() {
  const html = document.documentElement
  if (isDark.value) {
    html.classList.add('dark')
  } else {
    html.classList.remove('dark')
  }
}
```

#### 切换逻辑

```typescript
function toggleDark() {
  isDark.value = !isDark.value
  applyDarkMode()
  localStorage.setItem('mirro-dark-mode', isDark.value ? 'dark' : 'light')
}
```

#### 系统主题监听

```typescript
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  if (!localStorage.getItem('mirro-dark-mode')) {
    isDark.value = e.matches
    applyDarkMode()
  }
})
```

仅当用户没有手动设置时，才跟随系统主题变化。一旦用户手动切换过，以用户选择为准。

#### 组件通信

通过 props/emit 传递给 NavBar：

```html
<NavBar :is-dark="isDark" @toggle-dark="toggleDark" />
```

### 切换按钮

**文件:** [frontend/src/components/NavBar.vue](../../frontend/src/components/NavBar.vue)

导航栏右侧新增暗色模式切换按钮：

```html
<button @click="$emit('toggleDark')">
  <!-- 亮色模式 → 显示太阳图标 ☀️ -->
  <svg v-if="!isDark">...</svg>
  <!-- 暗色模式 → 显示月亮图标 🌙 -->
  <svg v-else>...</svg>
</button>
```

### 配色方案

#### 亮色模式 (默认)

| 元素 | 颜色 |
|------|------|
| 页面背景 | `bg-slate-50` (#f8fafc) |
| 卡片背景 | `bg-white` (#ffffff) |
| 主文字 | `text-slate-900` (#0f172a) |
| 次要文字 | `text-slate-500` (#64748b) |
| 边框 | `border-slate-200` (#e2e8f0) |
| 输入框背景 | `bg-white` (#ffffff) |

#### 暗色模式

| 元素 | Tailwind Class | 颜色 |
|------|---------------|------|
| 页面背景 | `dark:bg-slate-900` | #0f172a |
| 卡片背景 | `dark:bg-slate-800` | #1e293b |
| 主文字 | `dark:text-slate-100` | #f1f5f9 |
| 次要文字 | `dark:text-slate-400` | #94a3b8 |
| 边框 | `dark:border-slate-700` | #334155 |
| 输入框背景 | `dark:bg-slate-800` | #1e293b |

#### CSS 变量覆盖

```css
:root {
  --color-primary: #6366f1;
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-text: #1e293b;
  --color-text-muted: #94a3b8;
}

.dark {
  --color-primary: #818cf8;
  --color-bg: #0f172a;
  --color-surface: #1e293b;
  --color-text: #e2e8f0;
  --color-text-muted: #64748b;
}
```

### 各组件暗色适配

#### 全局布局 (App.vue)

```html
<div class="min-h-screen bg-slate-50 dark:bg-slate-900 transition-colors duration-300">
```

添加 `transition-colors duration-300` 实现背景色平滑过渡。

#### 导航栏 (NavBar.vue)

```html
<nav class="... bg-white/80 dark:bg-slate-900/80 ... dark:border-slate-700">
```

激活链接：
```html
bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300
```

非激活链接：
```
text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800
```

#### 问题输入 (QuestionInput.vue)

```css
textarea: dark:bg-slate-800 dark:text-slate-200 dark:border-slate-600
         dark:placeholder:text-slate-500
按钮:    dark:bg-indigo-500 dark:hover:bg-indigo-600
禁用:    dark:disabled:bg-slate-700
kbd:     dark:bg-slate-700
```

#### 流式答案 (StreamingAnswer.vue)

```css
内容区: dark:bg-slate-800 dark:border-slate-700
完成标记: dark:text-green-400 dark:border-slate-700
复制按钮: dark:bg-slate-800 dark:border-slate-600
```

#### Markdown 渲染（main.css）

```css
.dark .markdown-body code { background: #334155; color: #e2e8f0; }
.dark .markdown-body pre { background: #0f172a; color: #cbd5e1; }
.dark .markdown-body blockquote { border-left-color: var(--color-primary); }
```

#### 骨架屏 (SkeletonLoader.vue + main.css)

```css
.dark .skeleton-shimmer-dark {
  background: linear-gradient(90deg, #334155 25%, #475569 50%, #334155 75%);
}
```

#### Mermaid 流程图容器（main.css）

```css
.dark .mermaid-container {
  background: #1e293b;
  border-color: #334155;
}
```

#### 历史卡片 (HistoryView.vue)

渐变色卡片在暗色模式下使用深色调：
```
dark:from-indigo-950 dark:via-slate-900 dark:to-violet-950 dark:border-indigo-800/30
```

文字色调：
```
dark:text-indigo-200 dark:group-hover:text-indigo-300
dark:text-slate-400 dark:text-slate-500
```

#### 统计看板 (DashboardView.vue)

```html
卡片: dark:bg-slate-800 dark:border-slate-700
数字: dark:text-indigo-400 dark:text-emerald-400 dark:text-amber-400
标签: dark:text-slate-400
标题: dark:text-slate-300 dark:text-slate-100
```

#### 答案详情 (QuestionView.vue)

```html
问题卡片: dark:bg-slate-800 dark:border-amber-800/20
问题文字: dark:text-amber-200
section标题: dark:text-slate-200
提示框: dark:bg-indigo-950 dark:border-indigo-800 dark:text-indigo-300
反馈按钮: dark:bg-slate-800 dark:border-slate-700
追问输入: dark:bg-slate-800 dark:text-slate-200 dark:border-slate-700
```

### 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 暗色模式策略 | class-based (`.dark` 类) | Tailwind v4 推荐方式，简单可控 |
| 状态存储 | localStorage | 跨 session 持久化 |
| 默认行为 | 跟随系统偏好 | 无 localStorage 时尊重用户 OS 设置 |
| 系统监听 | matchMedia change | 实时响应用户 OS 主题切换 |
| 过度动画 | `transition-colors duration-300` | 避免突兀的颜色跳变 |
| 暗色主题 | slate 深色调 | 与亮色的 slate 体系一致，降低对比度 |
