/**
 * Mirro API 客户端
 * 封装所有与后端 Python FastAPI 的通信逻辑。
 * 业务场景：前端所有数据请求统一通过此模块，避免在各组件中散落fetch调用。
 */

// 后端API基础路径（开发环境走Vite代理，生产环境同域部署）
const API_BASE = '/api'

/**
 * 通用GET请求
 * 用于获取问题列表、问题详情、统计数据等只读操作
 */
export async function apiGet<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, String(value))
    })
  }
  const res = await fetch(url.toString())
  if (!res.ok) {
    throw new Error(`API 请求失败: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

/**
 * 通用POST请求
 * 用于提交新问题、搜索等写操作
 */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(`API 请求失败: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

/**
 * 通用DELETE请求
 * 用于删除问题记录
 */
export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE' })
  if (!res.ok) {
    throw new Error(`API 请求失败: ${res.status} ${res.statusText}`)
  }
}

/**
 * SSE流式请求 — 核心业务方法
 * 提交问题后，通过EventSource接收后端SSE流式推送。
 * 业务场景：答案生成是分阶段推送的（分类→正文→流程图→步骤→来源→完成），
 * 前端通过回调函数分别处理每个阶段的数据。

 * @param question 用户提问内容
 * @param onEvent 每收到一个SSE事件时的回调 (eventType, data)
 * @param onError 连接出错时的回调
 * @returns 返回EventSource实例，调用方可通过 .close() 中断
 */
export function streamQuestion(
  question: string,
  onEvent: (type: string, data: string) => void,
  onError?: (error: string) => void
): EventSource {
  // 通过POST无法直接使用EventSource（只支持GET），改用fetch+ReadableStream
  // 这里使用fetch POST + SSE解析
  const controller = new AbortController()

  fetch(`${API_BASE}/questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: question }),
    signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) {
      onError?.(`请求失败: ${response.status}`)
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      onError?.('无法读取响应流')
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    // 持续读取SSE数据流，直到后端关闭连接
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE格式：事件以双换行分隔
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''  // 最后一个可能不完整，保留到下次处理

      for (const part of parts) {
        const lines = part.split('\n')
        let eventType = ''
        let eventData = ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            // 多行data合并（如Markdown段落含换行时，后端按SSE规范拆为多个data行）
            eventData += (eventData ? '\n' : '') + line.slice(6).trim()
          }
        }

        if (eventType) {
          onEvent(eventType, eventData)
        }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onError?.(err.message)
    }
  })

  // 返回一个类似EventSource的对象，支持close()
  return {
    close: () => controller.abort(),
    onerror: null,
    onmessage: null,
    readyState: 0,
    url: '',
    withCredentials: false,
  } as unknown as EventSource
}

/** 获取问题历史列表 */
export function fetchQuestions(page = 1, size = 20) {
  return apiGet<{ items: import('@/types').QuestionResponse[]; total: number; page: number; size: number }>(
    '/questions', { page, size }
  )
}

/** 获取问题详情（含答案） */
export function fetchQuestionDetail(id: string) {
  return apiGet<import('@/types').QuestionDetail>(`/questions/${id}`)
}

/** 删除问题 */
export function deleteQuestion(id: string) {
  return apiDelete(`/questions/${id}`)
}

/** 手动搜索 */
export function searchWeb(query: string, maxResults = 5) {
  return apiPost<import('@/types').SearchResponse>('/search', { query, max_results: maxResults })
}

/** 获取统计数据 */
export function fetchStats() {
  return apiGet<import('@/types').StatsOverview>('/questions/stats')
}
