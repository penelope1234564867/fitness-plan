/**
 * SSE（Server-Sent Events）流式响应解析器
 *
 * 后端 POST /fitness/init-plan 和 POST /fitness/generate-next
 * 用 SSE 流式返回进度事件。因请求是 POST，故用 fetch + ReadableStream 替代 EventSource。
 */
import type { SSEEventCallbacks, WeekPlan } from '@/types'

/**
 * 解析 SSE 流式响应
 *
 * 后端事件格式：
 *   event: progress
 *   data: {"phase":"search","text":"📡 正在搜索动作..."}
 *
 *   event: day_done
 *   data: {"day":1,"focus":"胸部","main_count":3}
 *
 *   event: done
 *   data: { ... 完整 WeekPlan 数据 ... }
 *
 *   event: error
 *   data: {"text":"生成失败: ..."}
 */
export async function consumeSSE(
  response: Response,
  callbacks: SSEEventCallbacks,
): Promise<WeekPlan> {
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE 以 \n\n 分隔事件
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''

    for (const block of blocks) {
      const parsed = _parseSSEBlock(block)
      if (!parsed) continue

      const { eventType, dataStr } = parsed

      try {
        const data = JSON.parse(dataStr)

        switch (eventType) {
          case 'progress':
            callbacks.onProgress?.(data as any)
            break
          case 'day_done':
            callbacks.onDayDone?.(data as any)
            break
          case 'done':
            callbacks.onDone?.(data as WeekPlan)
            return data as WeekPlan
          case 'error':
            callbacks.onError?.(data as any)
            throw new Error(data.text || '生成失败')
        }
      } catch (e) {
        if (e instanceof SyntaxError) {
          console.warn('[SSE] JSON 解析失败:', dataStr)
        } else {
          throw e
        }
      }
    }
  }

  throw new Error('SSE 流提前结束，未收到 done 事件')
}

/**
 * 解析单个 SSE block（event + data 行）
 */
function _parseSSEBlock(block: string): { eventType: string; dataStr: string } | null {
  const lines = block.split('\n')
  let eventType = ''
  let dataStr = ''

  for (const line of lines) {
    if (line.startsWith('event: ')) {
      eventType = line.slice(7).trim()
    } else if (line.startsWith('data: ')) {
      dataStr = line.slice(6)
    }
  }

  if (!dataStr) return null
  return { eventType, dataStr }
}

/**
 * 生成进度估算（根据 phase 估算 0-100）
 *
 * 新引擎 (init-plan):
 *   init → coordinator → search → llm_parallel → select → assemble → save → done
 *
 * 新引擎 (generate-next):
 *   init → analysis → read → decision → mesocycle → pool → create → config
 *   → llm → candidates → select → assemble → overload → save → finalize → done
 *
 * 若事件自带 progress 字段 (后端 v2+)，优先使用 data.progress；
 * 否则用此函数按 phase 名称估算。
 */
export function estimateProgress(phase: string): number {
  const phases: Record<string, number> = {
    // init-plan
    'init': 5,
    'coordinator': 8,
    'search': 20,
    'llm_parallel': 30,
    // generate-next
    'analysis': 8,
    'read': 7,
    'decision': 12,
    'mesocycle': 15,
    'pool': 22,
    'create': 26,
    'config': 29,
    'candidates': 34,
    'overload': 58,
    'finalize': 96,
    // shared
    'select': 45,
    'assemble': 55,
    'save': 75,
    'done': 100,
    // fallback
  }
  return phases[phase] ?? 50
}

/**
 * 从进度事件获取最佳进度值。
 * 优先使用后端传来的 progress 字段，否则按 phase 估算。
 */
export function getProgress(data: { progress?: number; phase?: string }): number {
  if (typeof data.progress === 'number') {
    return Math.min(100, Math.max(0, data.progress))
  }
  return estimateProgress(data.phase || '')
}
