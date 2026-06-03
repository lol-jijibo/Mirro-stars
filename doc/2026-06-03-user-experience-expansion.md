# 2026-06-03 用户体验扩展功能说明

本文记录本次围绕用户体验完成的三项扩展：提问澄清向导、答案顶部行动摘要、执行清单。
这三项功能围绕同一条用户链路展开：让用户把问题问清楚、快速抓住答案重点，并把方案真正推进下去。

## 一、功能扩展概览

| 功能 | 使用位置 | 解决的问题 | 对用户的便利性 |
| --- | --- | --- | --- |
| 提问澄清向导 | 首页提问区 | 用户问题太泛，AI 容易给出通用答案 | 帮用户补充现状、目标、限制，提升答案贴合度 |
| 答案顶部行动摘要 | 答案详情页、分享页 | 答案较长，用户不容易马上抓住重点 | 先展示结论、第一步、周期、风险和适用场景 |
| 执行清单 | 答案详情页步骤区域 | 方案只是展示，用户看完后难以持续跟进 | 支持勾选状态、记录备注、保存执行进度 |

## 二、提问澄清向导

### 业务场景

用户经常会输入比较宽泛的问题，例如：

- “我想转行怎么办”
- “我很迷茫怎么办”
- “怎么开始理财”
- “我和对象总吵架怎么办”

如果系统直接生成答案，AI 很容易给出泛泛的建议。本次新增澄清向导，在问题明显偏宽泛时，先收集三类信息：

- 你的现状
- 想要的结果
- 时间、预算或其他限制

用户可以选择补充后生成，也可以直接跳过澄清。

### 用户便利性

- 降低提问门槛，用户不需要一开始就写出完整、专业的问题。
- 答案更贴合用户真实处境，减少“看起来正确但不适合我”的情况。
- 追问和相关推荐自动提交时不会弹出澄清向导，保证连续对话流畅。

### 核心代码位置

| 文件 | 核心职责 |
| --- | --- |
| `frontend/src/components/ClarificationWizard.vue` | 澄清向导 UI，收集现状、目标、限制 |
| `frontend/src/views/HomeView.vue` | 判断是否需要澄清，并把上下文传给后端 |
| `frontend/src/api/client.ts` | `streamQuestion` 新增 `clarificationContext` 参数 |
| `backend/app/models/schemas.py` | `QuestionCreate` 新增 `clarification_context` 字段 |
| `backend/app/api/questions.py` | 将澄清信息拼接进 AI 生成上下文 |

### 核心方法代码

`frontend/src/views/HomeView.vue`

```ts
function shouldAskClarification(question: string) {
  if (route.query.conversation_id) return false
  const normalized = question.trim()
  const broadSignals = ['怎么办', '怎么规划', '如何规划', '迷茫', '不知道', '怎么选择', '转行', '学习', '理财', '焦虑', '关系']
  const hasSpecificDetail = /\d|个月|年|预算|每天|每周|基础|经验|城市|收入|目标/.test(normalized)
  return normalized.length < 24 || (broadSignals.some(signal => normalized.includes(signal)) && !hasSpecificDetail)
}
```

这段逻辑用于识别短问题或泛化问题。普通首次提问会触发澄清，追问场景通过 `conversation_id` 直接跳过。

`frontend/src/views/HomeView.vue`

```ts
function startGeneration(question: string, clarificationContext = '') {
  errorMessage.value = ''
  showClarification.value = false
  pendingQuestion.value = ''
  isGenerating.value = true

  const convId = (route.query.conversation_id as string) || ''
  store.startStreaming(question, convId)

  activeStream.value = streamQuestion(
    question,
    handleSseEvent,
    handleSseError,
    convId || undefined,
    clarificationContext || undefined
  )
}
```

这段逻辑负责把原始问题和澄清上下文一起提交。原始问题用于页面和历史展示，澄清上下文只参与 AI 生成。

`backend/app/api/questions.py`

```py
generation_content = content
if clarification_context and clarification_context.strip():
    generation_content = f"{content}\n\n用户补充信息：\n{clarification_context.strip()}"

search_task = asyncio.create_task(search_related_resources(generation_content))
ai_result = await generate_answer(generation_content, history=conversation_history)
```

后端不会覆盖原始问题，而是构造 `generation_content` 作为 AI 和搜索服务的输入，使生成结果更完整。

## 三、答案顶部行动摘要

### 业务场景

Mirro 的答案通常包含正文、流程图、步骤、来源。长答案虽然完整，但用户进入详情页时需要先知道：

- 这个答案的核心判断是什么
- 我现在应该先做什么
- 大概需要多久
- 最大风险是什么
- 这个方案是否适合我

因此本次让 AI 在生成答案时同步输出 `action_summary`，并在正文前优先展示。

### 用户便利性

- 用户不用阅读完整答案，就能先判断方向是否有用。
- 降低长答案阅读压力，提高答案页的首屏价值。
- 分享页也展示摘要，接收分享的人能快速理解重点。

### 核心代码位置

| 文件 | 核心职责 |
| --- | --- |
| `backend/app/services/ai_service.py` | 扩展 AI 输出规范，要求返回 `action_summary` |
| `backend/app/models/schemas.py` | 新增 `ActionSummary` 模型 |
| `backend/app/models/database.py` | `answers` 表新增 `action_summary` 字段 |
| `backend/app/api/questions.py` | SSE 推送 `action_summary` 并保存入库 |
| `backend/app/api/answers.py` | 分享页接口返回 `action_summary` |
| `frontend/src/components/ActionSummaryPanel.vue` | 摘要展示组件 |
| `frontend/src/views/QuestionView.vue` | 答案详情页展示摘要 |
| `frontend/src/views/ShareView.vue` | 分享页展示摘要 |

### 核心方法代码

`backend/app/services/ai_service.py`

```py
"action_summary": {
    "conclusion": "...",
    "first_action": "...",
    "timeframe": "...",
    "risk": "...",
    "fit_for": "..."
}
```

AI 输出结构中新增 `action_summary`。字段分别对应核心结论、第一步行动、预计周期、主要风险和适用场景。

`backend/app/api/questions.py`

```py
action_summary = ai_result.get("action_summary") or {}
if isinstance(action_summary, dict) and action_summary:
    yield f"event: action_summary\ndata: {json.dumps(action_summary, ensure_ascii=False)}\n\n"
```

该逻辑通过 SSE 在正文前推送摘要，让前端能更早展示答案重点。

`frontend/src/stores/question.ts`

```ts
const streamingActionSummary = ref<ActionSummary | null>(null)

function setActionSummary(summary: ActionSummary) {
  streamingActionSummary.value = summary
}
```

Pinia store 新增流式摘要状态，保证答案刚生成后跳转详情页时不用等待接口重新拉取。

`frontend/src/views/QuestionView.vue`

```vue
<ActionSummaryPanel
  v-if="actionSummary"
  :summary="actionSummary"
/>
```

答案详情页在正文之前展示摘要。旧答案没有该字段时不会展示，兼容历史数据。

## 四、执行清单

### 业务场景

原有 `SolutionSteps` 只负责展示步骤，用户看完方案后仍然需要自己记住进度。本次将步骤升级为执行清单：

- 每一步支持状态切换：待做、进行中、已完成、暂缓
- 每一步支持备注，记录执行卡点或复盘想法
- 当前问题的执行进度会保存到浏览器本地
- 分享页为只读模式，避免接收分享的人误改本地状态

### 用户便利性

- 用户可以把 AI 方案当作任务面板使用，而不是只阅读一次。
- 刷新页面后状态和备注仍然保留，方便持续跟进。
- 对职业规划、学习路线、健身计划、理财计划等行动型问题尤其有帮助。

### 核心代码位置

| 文件 | 核心职责 |
| --- | --- |
| `frontend/src/components/SolutionSteps.vue` | 执行清单组件，管理状态、备注、进度条、本地保存 |
| `frontend/src/views/QuestionView.vue` | 传入 `storage-key`，让每个问题独立保存进度 |
| `frontend/src/views/ShareView.vue` | 使用 `readonly` 模式展示步骤 |

### 核心方法代码

`frontend/src/components/SolutionSteps.vue`

```ts
type StepStatus = 'todo' | 'doing' | 'done' | 'paused'

interface StepState {
  status: StepStatus
  note: string
}
```

每个步骤都有独立状态和备注。状态用于进度管理，备注用于记录执行过程中的具体情况。

`frontend/src/components/SolutionSteps.vue`

```ts
const localKey = computed(() => props.storageKey ? `mirro-checklist-${props.storageKey}` : '')
```

本地保存键基于当前问题 ID 生成，避免不同问题之间的执行进度互相覆盖。

`frontend/src/components/SolutionSteps.vue`

```ts
function setStatus(step: number, status: StepStatus) {
  if (props.readonly) return
  const current = getStepState(step)
  stepStates.value = {
    ...stepStates.value,
    [step]: { ...current, status },
  }
}
```

用户切换步骤状态时，组件更新对应步骤的状态。只读模式下不会执行修改。

`frontend/src/components/SolutionSteps.vue`

```ts
function saveStates() {
  if (!localKey.value || props.readonly) return
  localStorage.setItem(localKey.value, JSON.stringify(stepStates.value))
}
```

执行状态和备注会保存到浏览器本地，使用户刷新页面后仍能继续跟进。

`frontend/src/views/QuestionView.vue`

```vue
<SolutionSteps :steps="steps" :storage-key="route.params.id as string" />
```

答案详情页传入当前问题 ID，让执行清单按问题维度保存。

`frontend/src/views/ShareView.vue`

```vue
<SolutionSteps :steps="data.answer.steps" readonly />
```

分享页只展示步骤，不开放状态和备注编辑。

## 五、整体数据流

```text
用户输入问题
  ↓
HomeView 判断是否需要澄清
  ↓
ClarificationWizard 收集补充信息
  ↓
streamQuestion 提交 content + clarification_context
  ↓
后端生成 generation_content
  ↓
AI 生成 action_summary + content + flowchart + steps + related_questions
  ↓
SSE 推送 category / type / action_summary / content / steps / sources / done
  ↓
QuestionView 展示行动摘要、正文、执行清单、来源
  ↓
SolutionSteps 在本地保存执行状态和备注
```

## 六、兼容性说明

- 旧答案没有 `action_summary` 时，答案页和分享页会自动隐藏行动摘要区域。
- 澄清上下文不会覆盖历史问题内容，历史列表仍展示用户原始提问。
- 执行清单保存于浏览器本地，不影响后端答案数据，也不会影响分享页只读展示。
- 后端启动时会自动为旧 `answers` 表补充 `action_summary` 字段。

## 七、验证结果

本次扩展已完成以下验证：

```bash
cd frontend
npm run build
```

前端类型检查和构建通过。

```bash
cd backend
..\.venv\Scripts\python.exe -m compileall app
```

后端 Python 编译检查通过。
