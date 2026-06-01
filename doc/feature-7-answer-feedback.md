# Feature 7: 答案反馈（👍👎）

## 需求背景

让用户对 AI 答案质量进行打分，帮助评估模型效果。收集的数据可用于：
- 统计答案满意度
- 发现低质量回答并优化 prompt
- 了解用户偏好

## 业务逻辑

### 用户操作流程

1. 用户查看 AI 答案
2. 看到底部的反馈区域：**"这个答案对你有帮助吗？"**
3. 点击 👍 或 👎
4. 可选：在弹出的文本框中填写具体原因
5. 提交反馈 → 显示感谢信息
6. 已提交过反馈的问题不再显示评分按钮

### 数据库设计

**文件:** [backend/app/models/database.py](../../backend/app/models/database.py)

```sql
CREATE TABLE IF NOT EXISTS feedback (
    id VARCHAR(36) PRIMARY KEY COMMENT '反馈唯一ID',
    question_id VARCHAR(36) NOT NULL COMMENT '关联的问题ID',
    answer_id VARCHAR(36) NOT NULL COMMENT '关联的答案ID',
    rating INT NOT NULL DEFAULT 0 COMMENT '评分：1=好评(👍), -1=差评(👎), 0=中性',
    comment TEXT COMMENT '可选的文字反馈',
    created_at VARCHAR(255) NOT NULL COMMENT '反馈时间',
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (answer_id) REFERENCES answers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

表设计要点：
- `rating` 只存储 1（好评）或 -1（差评），简洁明确
- `comment` 为可选字段，降低用户提交门槛
- 外键级联删除：问题被删除时反馈自动清理
- 使用 UUID 主键，与项目其他表保持一致

### 后端 API

**文件:** [backend/app/api/questions.py](../../backend/app/api/questions.py)

#### POST `/api/questions/{question_id}/feedback` — 提交反馈

```python
@router.post("/{question_id}/feedback")
async def submit_feedback(question_id: str, body: FeedbackCreate) -> dict:
```

请求体：
```json
{
  "answer_id": "uuid-of-answer",
  "rating": 1,
  "comment": "分析很到位，步骤也很清晰"  // 可选
}
```

业务校验：
1. 检查 question_id 对应的记录是否存在（404 if not）
2. 检查 answer_id 对应的记录是否存在且属于该问题（404 if not）
3. 插入 feedback 记录

#### GET `/api/questions/{question_id}/feedback` — 查询反馈

```python
@router.get("/{question_id}/feedback")
async def get_feedback(question_id: str) -> dict:
```

返回格式：
```json
{
  "feedbacks": [
    {
      "id": "feedback-uuid",
      "question_id": "question-uuid",
      "answer_id": "answer-uuid",
      "rating": 1,
      "comment": "分析很到位",
      "created_at": "2026-05-31T..."
    }
  ]
}
```

前端用此接口查询用户是否已对某问题提交过反馈。

### Schema 定义

**文件:** [backend/app/models/schemas.py](../../backend/app/models/schemas.py)

```python
class FeedbackCreate(BaseModel):
    answer_id: str = Field(...)
    rating: int = Field(..., ge=-1, le=1)
    comment: Optional[str] = Field(None, max_length=500)

class FeedbackResponse(BaseModel):
    id: str
    question_id: str
    answer_id: str
    rating: int
    comment: Optional[str]
    created_at: str
```

### 前端实现

**文件:** [frontend/src/views/QuestionView.vue](../../frontend/src/views/QuestionView.vue)

#### 状态管理

```typescript
const existingFeedback = ref<FeedbackResponse | null>(null)
const currentRating = ref(0)      // 1=👍, -1=👎, 0=未评分
const feedbackComment = ref('')
const isSubmittingFeedback = ref(false)
const feedbackSubmitted = ref(false)
const showCommentInput = ref(false)
```

#### 评分按钮

```
┌──────────────────────────────────────────────────────┐
│ 💬 这个答案对你有帮助吗？                              │
│                                                      │
│  ┌─────────────┐    ┌─────────────┐                  │
│  │ 👍 有帮助    │    │ 👎 不够好    │                  │
│  └─────────────┘    └─────────────┘                  │
└──────────────────────────────────────────────────────┘
```

点击后按钮变为选中态（绿色/红色高亮），并展开评论输入框：

```
┌──────────────────────────────────────────────────────┐
│ 💬 这个答案对你有帮助吗？                              │
│                                                      │
│  ┌─────────────┐    ┌─────────────┐                  │
│  │ 👍 有帮助    │ ✗  │ 👎 不够好    │                  │
│  └─────────────┘    └─────────────┘                  │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │ 可选：告诉我们哪里好或哪里需要改进…          │    │
│  └──────────────────────────────────────────────┘    │
│  [提交反馈]  [取消]                                   │
└──────────────────────────────────────────────────────┘
```

#### 已提交状态

```
┌──────────────────────────────────────────────────────┐
│ ✅ 感谢你的反馈！很高兴能帮到你 👍                     │
└──────────────────────────────────────────────────────┘
```

#### 交互逻辑

```typescript
// 点击评分按钮
function handleRate(rating: number) {
  if (feedbackSubmitted.value) return
  currentRating.value = rating
  showCommentInput.value = true
}

// 提交反馈（含可选评论）
async function handleSubmitFeedback() {
  if (feedbackSubmitted.value || currentRating.value === 0) return
  // 调用 API
  await submitFeedback(route.params.id as string, {
    answer_id: answerId,
    rating: currentRating.value,
    comment: feedbackComment.value.trim() || undefined,
  })
  feedbackSubmitted.value = true
  showCommentInput.value = false
}

// 取消评论
function cancelComment() {
  showCommentInput.value = false
  feedbackComment.value = ''
  if (!feedbackSubmitted.value) currentRating.value = 0
}
```

#### 反馈加载时机

```typescript
onMounted(() => {
  if (!isFromStream.value) {
    loadQuestionDetail()   // 内部会调用 loadExistingFeedback()
  } else {
    loadExistingFeedback() // 从SSE流过来的也加载反馈
  }
})
```

#### API 封装

**文件:** [frontend/src/api/client.ts](../../frontend/src/api/client.ts)

```typescript
export function submitFeedback(questionId: string, feedback: FeedbackCreate) {
  return apiPost(`/questions/${questionId}/feedback`, feedback)
}

export function fetchFeedback(questionId: string) {
  return apiGet<{ feedbacks: FeedbackResponse[] }>(`/questions/${questionId}/feedback`)
}
```

### 数据用途

收集的反馈数据可用于：

1. **模型效果评估** — 统计好评率，按分类/时间维度分析
2. **Prompt 优化** — 分析差评问题的共性，改进 system prompt
3. **用户体验改进** — 根据反馈评论了解用户真实需求

未来可扩展：
- 反馈统计看板（DashboardView 新增面板）
- 基于反馈的答案排序/推荐
- 自动标记低质量答案进行人工审核
