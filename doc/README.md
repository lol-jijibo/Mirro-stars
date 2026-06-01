# Mirro 功能实现文档

> 本文档记录 2026-05-31 实现的四项核心功能改进。

## 功能列表

| 序号 | 功能 | 投入 | 文档 |
|------|------|------|------|
| 5 | 历史页 — 搜索 + 分类筛选 | 🟡 中投入 | [feature-5-history-search-filter.md](feature-5-history-search-filter.md) |
| 6 | AI 多轮对话 | 🟡 中投入 | [feature-6-multi-turn-conversation.md](feature-6-multi-turn-conversation.md) |
| 7 | 答案反馈（👍👎） | 🟡 中投入 | [feature-7-answer-feedback.md](feature-7-answer-feedback.md) |
| 8 | 深色模式 | 🟡 中投入 | [feature-8-dark-mode.md](feature-8-dark-mode.md) |

## 修改文件总览

### 后端（Python FastAPI）

| 文件 | 修改类型 | 涉及功能 |
|------|----------|----------|
| `backend/app/models/schemas.py` | 新增字段和模型 | 5, 6, 7 |
| `backend/app/models/database.py` | 新增表和列 | 6, 7 |
| `backend/app/services/ai_service.py` | 修改函数签名 | 6 |
| `backend/app/api/questions.py` | 修改+新增端点 | 5, 6, 7 |

### 前端（Vue 3 + TypeScript）

| 文件 | 修改类型 | 涉及功能 |
|------|----------|----------|
| `frontend/src/types/index.ts` | 新增类型 | 6, 7 |
| `frontend/src/api/client.ts` | 修改+新增方法 | 5, 6, 7 |
| `frontend/src/stores/question.ts` | 新增字段 | 6 |
| `frontend/src/assets/main.css` | 新增样式 | 8 |
| `frontend/src/App.vue` | 新增暗色模式管理 | 8 |
| `frontend/src/components/NavBar.vue` | 新增切换按钮 | 8 |
| `frontend/src/views/HistoryView.vue` | 重写 | 5, 8 |
| `frontend/src/views/HomeView.vue` | 修改 | 6, 8 |
| `frontend/src/views/QuestionView.vue` | 大幅修改 | 6, 7, 8 |
| `frontend/src/views/DashboardView.vue` | 新增暗色变体 | 8 |
| `frontend/src/components/QuestionInput.vue` | 新增暗色变体 | 8 |
| `frontend/src/components/StreamingAnswer.vue` | 新增暗色变体 | 8 |
| `frontend/src/components/SkeletonLoader.vue` | 新增暗色变体 | 8 |

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Vite)                    │
│                                                         │
│  HistoryView ── 搜索框 + 分类下拉 → 后端查询              │
│  HomeView ── 支持 conversation_id 查询参数               │
│  QuestionView ── 反馈按钮 + 追问输入 + 暗色模式            │
│  App.vue ── 暗色模式状态管理 (localStorage)              │
│  NavBar ── 暗色模式切换按钮                               │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP / SSE
┌────────────────────┴────────────────────────────────────┐
│                 后端 (FastAPI)                            │
│                                                         │
│  GET /api/questions?search=&category=  ← 搜索+分类筛选    │
│  POST /api/questions { content, conversation_id } ← 多轮  │
│  POST /api/questions/:id/feedback ← 反馈提交              │
│  GET /api/questions/:id/feedback ← 反馈查询               │
│  SSE _stream_answer() ← 支持历史对话拼接                   │
└────────────────────┬────────────────────────────────────┘
                     │ aiomysql
┌────────────────────┴────────────────────────────────────┐
│                    MySQL 数据库                           │
│                                                         │
│  questions ── +conversation_id 列                        │
│  answers (无变化)                                        │
│  feedback (新建) ── id, question_id, answer_id,          │
│                       rating, comment, created_at        │
└─────────────────────────────────────────────────────────┘
```
