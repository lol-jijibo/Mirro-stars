# 用户体验增强 — 长内容导航与交互优化

日期：2026-06-03

## 概述

针对答案详情页（QuestionView）和分享页（ShareView）的3项高优先级用户体验增强：

1. **Markdown 正文目录导航 (TOC)**
2. **代码块一键复制按钮**
3. **阅读进度条 + 回到顶部**

---

## 1. 正文目录导航 (TOC)

### 解决的问题
AI 生成的答案通常很长，包含多个段落和子主题。用户缺乏快速定位的手段，只能手动滚动查找感兴趣的部分。

### 实现方案

**新组件：`AnswerToc.vue`**

- 从 Markdown 原文中提取 h2/h3/h4 标题，生成浮动目录
- 使用 `IntersectionObserver` 实时高亮当前阅读位置
- 点击目录项平滑滚动到对应标题
- 仅在 **xl 屏幕（≥1280px）** 显示，小屏隐藏避免挤压内容区
- 仅在有 **2 个以上标题** 时显示，避免无意义的空目录
- 位置：固定在内容区左侧，与正文形成左右布局

**配套修改：`StreamingAnswer.vue`**
- 覆写 `markdown-it` 的 `heading_open` 渲染规则，为 h2/h3/h4 自动添加 `id` 属性和 `scroll-mt-20` 类（避免被顶部导航栏遮挡）

### 涉及文件
- `frontend/src/components/AnswerToc.vue` — 新建
- `frontend/src/components/StreamingAnswer.vue` — 添加标题锚点
- `frontend/src/views/QuestionView.vue` — 引入组件

---

## 2. 代码块一键复制

### 解决的问题
AI 答案中经常包含代码示例、命令行、配置文件等。用户之前只能通过"复制全文"按钮复制整个 Markdown 原文，无法快速复制单个代码片段。

### 实现方案

**修改：`StreamingAnswer.vue`**

- 覆写 `markdown-it` 的 `fence` 渲染规则，包裹代码块：
  - 顶部 header 栏：左侧显示语言标签（如 `python`、`bash`），右侧复制按钮
  - 默认隐藏复制按钮（`opacity: 0`），hover 代码块时显示
  - 复制成功后按钮状态切换为"已复制"（绿色），2 秒后恢复
  - 降级方案：`clipboard API` 不可用时，使用 `document.execCommand('copy')` + 选区
- 使用**事件代理**模式：在容器上绑定 `@click`，通过 `closest('.code-copy-btn')` 判断是否点击了复制按钮

**样式处理**
- 代码块暗色背景（`#1e293b`），header 稍亮（`#334155`）
- 按钮采用半透明设计，hover 时加深
- `pre` 的 margin 重置，避免与 wrapper 的圆角冲突

### 涉及文件
- `frontend/src/components/StreamingAnswer.vue` — 核心修改

---

## 3. 阅读进度条 + 回到顶部

### 解决的问题
- 用户阅读长答案时没有位置感知，不知道还有多少内容未读
- 滚动到底部后，需要手动滚回顶部查看问题或导航，操作繁琐

### 实现方案

**新组件：`ReadingProgress.vue`**

**阅读进度条**
- 固定在页面最顶部（`z-[60]`，高于导航栏的 `z-50`）
- 高度 3px，渐变色（indigo → purple → pink）
- 使用 `requestAnimationFrame` 节流，滚动性能友好
- `passive: true` 事件监听器，不阻塞主线程

**回到顶部按钮**
- 右下角 FAB 按钮，滚动超过 400px 时出现
- 点击平滑滚动回顶部（`scrollTo({ behavior: 'smooth' })`）
- 带进入/离开过渡动画（`<Transition>` + CSS）
- 圆形设计，与页面风格协调
- 在分享页（ShareView）同样可用

### 涉及文件
- `frontend/src/components/ReadingProgress.vue` — 新建
- `frontend/src/views/QuestionView.vue` — 引入
- `frontend/src/views/ShareView.vue` — 引入

---

## 技术要点

| 要点 | 说明 |
|------|------|
| TOC 标题提取 | 正则 `^(#{2,4})\s+(.+)$` 从 Markdown 原文解析，去除了 markdown 格式字符 |
| TOC 激活追踪 | `IntersectionObserver`，`rootMargin: '-80px 0px -70% 0px'`，优先展示最靠上的可见标题 |
| 代码块复制 | 事件代理，`closest()` 定位按钮和代码元素，clipboard API + execCommand 降级 |
| 进度条性能 | `requestAnimationFrame` + `passive` scroll listener |
| CSS `v-bind` 注意 | Vue SFC `style` 中的 `v-bind()` 在 inline style 中存在引号冲突，改用 `:style` 绑定 computed 属性 |

---

## 影响范围

- **QuestionView** — 核心答案详情页，3 项功能全部生效
- **ShareView** — 分享页，进度条 + 回到顶部 + 代码块复制（StreamingAnswer 组件自带）生效
- **StreamingAnswer** — 所有使用该组件的地方自动获得代码块复制和标题锚点能力
