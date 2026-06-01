# Feature 6: AI 多轮对话

## 需求背景

当前每次提问都是独立上下文，用户无法追问。比如第一次问了"如何转行学编程"，AI 给了学习路线，用户想追问"那前端和后端哪个更适合我？"时，AI 不知道之前的对话内容，需要用户重复描述背景。

## 业务逻辑

### 用户操作流程

1. 用户在首页提问 → 正常 SSE 流式生成答案
2. 用户进入答案详情页，在底部看到追问输入框
3. 用户输入追问内容（如"能详细说说第二步吗？"）
4. 点击追问按钮 → 跳转到首页，URL 携带 `?conversation_id=xxx&follow_up=yyy`
5. 首页自动提交追问，后端拼接历史对话后调用 LLM
6. 用户看到结合了前文的新答案

### 后端实现

#### conversation_id 设计

`conversation_id` 是会话标识符：
- **首次提问**：`conversation_id = NULL`（无上下文）
- **追问**：`conversation_id = 首次提问的 question_id`
- 同一轮对话的所有问题共享同一个 `conversation_id`
- 后端查询时通过 `WHERE q.id = ? OR q.conversation_id = ?` 加载整轮对话

#### 数据库变更

**文件:** [backend/app/models/database.py](../../backend/app/models/database.py)

```sql
-- questions 表新增列
ALTER TABLE questions ADD COLUMN conversation_id VARCHAR(36)
  COMMENT '多轮对话的会话ID，同一轮对话的所有问题共享此ID'
  AFTER category;
```

兼容迁移：使用 `ALTER TABLE ... ADD COLUMN` + try/except，旧表自动升级。

#### Schema 变更

**文件:** [backend/app/models/schemas.py](../../backend/app/models/schemas.py)

```python
class QuestionCreate(BaseModel):
    content: str = Field(...)
    conversation_id: Optional[str] = Field(None, ...)  # 新增
```

#### SSE 流式生成增强

**文件:** [backend/app/api/questions.py](../../backend/app/api/questions.py)

`_stream_answer()` 新增阶段 0.5：获取对话历史。

```python
async def _stream_answer(question_id, content, category, conversation_id=None):
    # ...
    # 阶段0.5：获取多轮对话历史
    conversation_history = None
    if conversation_id:
        history_rows = await db.execute_fetchall(
            """SELECT q.content, a.content as answer_content
               FROM questions q
               LEFT JOIN answers a ON q.id = a.question_id
               WHERE (q.id = ? OR q.conversation_id = ?) AND a.content IS NOT NULL
               ORDER BY q.created_at ASC""",
            (conversation_id, conversation_id)
        )
        if history_rows:
            conversation_history = []
            for row in history_rows:
                conversation_history.append({"role": "user", "content": row[0]})
                if row[1]:
                    truncated = row[1][:2000] + ("..." if len(row[1]) > 2000 else "")
                    conversation_history.append({"role": "assistant", "content": truncated})
```

关键设计：
1. 查询条件 `q.id = ? OR q.conversation_id = ?` — 加载会话链上的所有问答
2. 按 `created_at ASC` 排序 — 保证对话时序正确
3. 答案内容截断到 2000 字符 — 避免 token 过长超出 LLM 上下文窗口
4. `LEFT JOIN answers` — 处理答案可能不存在的情况

#### AI 服务增强

**文件:** [backend/app/services/ai_service.py](../../backend/app/services/ai_service.py)

```python
async def generate_answer(question: str, history: list[dict] | None = None) -> dict:
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)  # 插入历史对话
    messages.append({"role": "user", "content": question})

    response = await _retry_call(client=client, messages=messages, ...)
```

LLM 实际收到的消息结构：
```
[system] 你是一个年轻人问题解决专家...
[user]   我25岁想转行做程序员，零基础该怎么规划？
[assistant] (上一个回答...)
[user]   那前端和后端哪个更适合我？  ← 当前追问
```

### 前端实现

#### Store 变更

**文件:** [frontend/src/stores/question.ts](../../frontend/src/stores/question.ts)

新增 `conversationId` 状态：

```typescript
const conversationId = ref('')

function startStreaming(question: string, convId: string = '') {
  // ...
  conversationId.value = convId
}
```

#### API Client 变更

**文件:** [frontend/src/api/client.ts](../../frontend/src/api/client.ts)

```typescript
export function streamQuestion(
  question: string,
  onEvent: ..., onError?: ...,
  conversationId?: string  // 新增参数
): EventSource {
  const body: Record<string, string> = { content: question }
  if (conversationId) {
    body.conversation_id = conversationId
  }
  // ...
}
```

#### 提问页面增强

**文件:** [frontend/src/views/HomeView.vue](../../frontend/src/views/HomeView.vue)

1. 支持从 URL query 读取 `conversation_id`：

```typescript
function handleSubmit(question: string) {
  const convId = (route.query.conversation_id as string) || ''
  store.startStreaming(question, convId)
  activeStream.value = streamQuestion(question, ..., convId || undefined)
}
```

2. 自动处理追问跳转：

```typescript
onMounted(() => {
  const followUp = route.query.follow_up as string
  if (followUp && followUp.trim().length >= 5) {
    // 清除 follow_up 参数（防刷新重复提交），保留 conversation_id
    router.replace({ path: '/', query: { conversation_id: route.query.conversation_id } })
    handleSubmit(followUp.trim())
  }
})
```

#### 追问输入区

**文件:** [frontend/src/views/QuestionView.vue](../../frontend/src/views/QuestionView.vue)

在答案详情页底部添加追问区域：

```
┌──────────────────────────────────────────────────────┐
│ 💬 继续追问                                          │
│ 对答案还有疑问？提出追问，AI 会结合之前的对话上下文...  │
│ ┌──────────────────────────────────┐ ┌─────────────┐ │
│ │ 输入你的追问…（至少5个字）        │ │  🔍 追问     │ │
│ └──────────────────────────────────┘ └─────────────┘ │
└──────────────────────────────────────────────────────┘
```

```typescript
function handleFollowUp() {
  const content = followUpContent.value.trim()
  if (!content || content.length < 5) return
  router.push({
    path: '/',
    query: {
      conversation_id: route.params.id as string,
      follow_up: content,
    },
  })
}
```

## 流程时序

```
用户        QuestionView          HomeView            后端              LLM
 │              │                    │                  │                │
 │ 输入追问     │                    │                  │                │
 │─────────────>│                    │                  │                │
 │              │ 跳转 /?conv_id=x   │                  │                │
 │              │ &follow_up=yyy     │                  │                │
 │              │───────────────────>│                  │                │
 │              │                    │ 读取 follow_up   │                │
 │              │                    │ 清除 query params│                │
 │              │                    │ POST /questions  │                │
 │              │                    │ {content, conv_id}                │
 │              │                    │─────────────────>│                │
 │              │                    │                  │ 查询历史对话    │
 │              │                    │                  │───────────────>│
 │              │                    │                  │<───────────────│
 │              │                    │                  │ generate_answer│
 │              │                    │                  │ with history   │
 │              │                    │<── SSE streaming ─────────────────│
 │              │                    │                  │                │
 │              │<─ SSE done ────────│                  │                │
 │<── 新答案页  │                    │                  │                │
```

## 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 历史截断长度 | 2000 字符/条 | 避免 token 溢出，保留足够上下文 |
| 追问跳转方式 | 返回首页自动提交 | 复用已有 SSE 流式生成逻辑，减少重复代码 |
| conversation_id 语义 | 指向首问 question_id | 简单直观，一轮对话一个 ID |
| URL 参数传递 | follow_up + conversation_id | 支持深度链接，刷新不丢失上下文 |
