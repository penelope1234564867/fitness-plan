import { describe, it, expect, vi } from 'vitest'
import { consumeSSE, estimateProgress } from '@/services/sse'

describe('consumeSSE', () => {
  function makeResponse(events: string): Response {
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(events))
        controller.close()
      },
    })
    return new Response(stream)
  }

  it('calls onProgress for each progress event', async () => {
    const onProgress = vi.fn()
    const onDone = vi.fn()

    await consumeSSE(makeResponse(
      'event: progress\ndata: {"phase":"search","text":"搜索中..."}\n\n' +
      'event: progress\ndata: {"phase":"llm","text":"LLM 精选..."}\n\n' +
      'event: done\ndata: {"id":1,"week_number":1,"status":"active","generated_at":"2026-07-01","mesocycle_phase":"foundational","days":[]}\n\n'
    ), { onProgress, onDone })

    expect(onProgress).toHaveBeenCalledTimes(2)
    expect(onProgress).toHaveBeenNthCalledWith(1, { phase: 'search', text: '搜索中...' })
    expect(onProgress).toHaveBeenNthCalledWith(2, { phase: 'llm', text: 'LLM 精选...' })
    expect(onDone).toHaveBeenCalledTimes(1)
  })

  it('returns WeekPlan on done event', async () => {
    const weekData = {
      id: 1, week_number: 1, status: 'active' as const,
      generated_at: '2026-07-01', mesocycle_phase: 'foundational', days: [],
    }
    const result = await consumeSSE(makeResponse(
      `event: done\ndata: ${JSON.stringify(weekData)}\n\n`
    ), {})

    expect(result.id).toBe(1)
    expect(result.week_number).toBe(1)
    expect(result.mesocycle_phase).toBe('foundational')
  })

  it('throws on error event', async () => {
    await expect(consumeSSE(makeResponse(
      'event: error\ndata: {"text":"生成失败: wger 超时"}\n\n'
    ), {})).rejects.toThrow('生成失败: wger 超时')
  })

  it('calls onError callback before throwing', async () => {
    const onError = vi.fn()
    await expect(consumeSSE(makeResponse(
      'event: error\ndata: {"text":"失败"}\n\n'
    ), { onError })).rejects.toThrow()

    expect(onError).toHaveBeenCalledWith({ text: '失败' })
  })

  it('handles partial chunks across multiple reads', async () => {
    const stream = new ReadableStream({
      start(controller) {
        // 分两次发送，模拟 TCP 分包
        controller.enqueue(new TextEncoder().encode('event: progress\nda'))
        controller.enqueue(new TextEncoder().encode(
          'ta: {"phase":"search","text":"搜索"}\n\n' +
          'event: done\ndata: {"id":1,"week_number":1,"status":"active","generated_at":"","mesocycle_phase":"foundational","days":[]}\n\n'
        ))
        controller.close()
      },
    })

    const onProgress = vi.fn()
    await consumeSSE(new Response(stream), { onProgress })
    expect(onProgress).toHaveBeenCalledWith({ phase: 'search', text: '搜索' })
  })
})

describe('estimateProgress', () => {
  it('maps init phase to 5', () => {
    expect(estimateProgress('init')).toBe(5)
  })

  it('maps done phase to 100', () => {
    expect(estimateProgress('done')).toBe(100)
  })

  it('returns 50 for unknown phase', () => {
    expect(estimateProgress('unknown_phase')).toBe(50)
  })
})
