# Feature 5: 历史页 — 搜索 + 分类筛选

## 需求背景

历史页原本只是简单的分页列表，数据多了之后用户很难找到特定问题。后端已有 `category` 字段，前端只需加搜索框 + 分类下拉即可。

## 业务逻辑

### 用户操作流程

1. 用户进入历史页 `/history`
2. 在搜索框输入关键词 → 300ms 防抖后自动发起查询
3. 从分类下拉选择特定分类 → 立即发起查询
4. 支持搜索+分类组合筛选
5. 清除搜索/选择"全部"恢复全量列表
6. 搜索结果为空时显示友好提示

### 后端实现

**文件:** [backend/app/api/questions.py](../../backend/app/api/questions.py)

修改 `GET /api/questions` 端点，新增两个可选查询参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `search` | `string` | 关键词搜索，对 `content` 字段做 `LIKE %xxx%` 模糊匹配 |
| `category` | `string` | 精确分类筛选，例如 "职业发展"、"情感关系" |

**SQL 动态构建:**

```python
conditions = []
params = []

if search.strip():
    conditions.append("content LIKE ?")
    params.append(f"%{search.strip()}%")

if category.strip():
    conditions.append("category = ?")
    params.append(category.strip())

where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
```

关键点：
- 使用参数化查询（`?` 占位符），防止 SQL 注入
- 搜索和分类可以同时生效（AND 关系）
- WHERE 子句在无筛选条件时为空，保持向后兼容

### 前端实现

**文件:** [frontend/src/views/HistoryView.vue](../../frontend/src/views/HistoryView.vue)

#### 搜索框

```
┌──────────────────────────────────────────────────┐
│ 🔍 搜索问题关键词...                          ✕  │
└──────────────────────────────────────────────────┘
```

- 输入框左侧有搜索图标
- 输入内容后右侧出现清除按钮（×）
- 使用 300ms 防抖（debounce timer），避免每次按键都请求

```typescript
function onSearchInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    page.value = 1
    loadQuestions()
  }, 300)
}
```

#### 分类下拉

```
┌──────────────────────────────────────┐
│ 📂 全部分类                      ▾  │
├──────────────────────────────────────┤
│ 全部                                │
│ 职业发展                            │
│ 情感关系                            │
│ 个人成长                            │
│ 理财规划                            │
│ 健康生活                            │
│ 社交技巧                            │
│ 其他                                │
└──────────────────────────────────────┘
```

- 7 个分类 + "全部"选项
- 使用原生 `<select>`，自定义下拉箭头（SVG background-image）
- 切换分类立即触发查询（无需额外按钮）

```typescript
function onCategoryChange() {
  page.value = 1
  loadQuestions()
}
```

#### API 调用

**文件:** [frontend/src/api/client.ts](../../frontend/src/api/client.ts)

```typescript
export function fetchQuestions(page = 1, size = 20, search = '', category = '') {
  const params: Record<string, string | number> = { page, size }
  if (search) params.search = search
  if (category) params.category = category
  return apiGet<{ items: QuestionResponse[]; total: number; page: number; size: number }>(
    '/questions', params
  )
}
```

只有非空参数才会加入请求，保持 API 调用精简。

#### 卡片增强

历史卡片列表新增了分类标签显示：

```html
<span v-if="q.category && q.category !== '分析中...'"
      class="text-xs px-2 py-0.5 rounded-full bg-white/60">
  {{ q.category }}
</span>
```

过滤掉占位分类"分析中..."（流式生成中的临时值）。

#### 空状态优化

当搜索结果为空时，显示区分性提示：
- 有筛选条件时："没有匹配的记录，试试其他关键词或分类"
- 无筛选条件时："还没有提问记录"

## 7 个分类体系

| 分类 | 典型问题 |
|------|----------|
| 职业发展 | 转行、升职、学习路线、面试 |
| 情感关系 | 恋爱、分手、人际矛盾 |
| 个人成长 | 自律、拖延、目标设定 |
| 理财规划 | 储蓄、投资、预算管理 |
| 健康生活 | 健身、饮食、心理健康 |
| 社交技巧 | 沟通、社交焦虑、人脉 |
| 其他 | 不在上述范围的问题 |
