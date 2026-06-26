import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  ConvTurn,
  DoneEvent,
  FeedItem,
  RunState,
  SSEEvent,
  ToolFeedItem,
  ToolState,
} from './sse-events'

export interface UseAgentRunOptions {
  /** POST to start a run. Caller constructs the body and returns the job_id. */
  startRun: () => Promise<string>
  /** Returns the SSE stream URL for a given jobId. */
  streamUrl: (jobId: string) => string
}

export interface UseAgentRunResult {
  feed: FeedItem[]
  runState: RunState
  elapsed: number
  answer: string | null
  errorMsg: string | null
  isRunning: boolean
  run: () => void
  clear: () => void
}

export function useAgentRun({ startRun, streamUrl }: UseAgentRunOptions): UseAgentRunResult {
  const [feed, setFeed]         = useState<FeedItem[]>([])
  const [runState, setRunState] = useState<RunState>('idle')
  const [elapsed, setElapsed]   = useState(0)
  const [answer, setAnswer]     = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const esRef            = useRef<EventSource | null>(null)
  const timerRef         = useRef<ReturnType<typeof setInterval> | null>(null)
  const itemIdRef        = useRef(0)
  // FIFO queue of feed-item IDs for pending tool cards — matches tool_start to tool_end in order
  const pendingToolsRef  = useRef<number[]>([])
  // Hold tool schemas until prompt_ready arrives, then merge into one context_ready item
  const pendingToolSchemasRef = useRef<Array<{ name: string; description: string; parameters: Record<string, unknown> }>>([])

  const stopTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const closeStream = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    stopTimer()
  }, [stopTimer])

  const handleEvent = useCallback((event: SSEEvent) => {
    if (event.type === 'heartbeat') return

    if (event.type === 'status') {
      setFeed(prev => [...prev, { kind: 'status', id: itemIdRef.current++, message: event.message }])
      return
    }

    if (event.type === 'tool_start') {
      const id = itemIdRef.current++
      pendingToolsRef.current = [...pendingToolsRef.current, id]
      setFeed(prev => [...prev, {
        kind: 'tool',
        id,
        tool: event.tool,
        tool_reasoning: event.tool_reasoning,
        args: event.args,
        state: 'pending' as ToolState,
        result_preview: '',
        has_error: false,
        error: '',
        latency_s: null,
      }])
      return
    }

    if (event.type === 'tool_end') {
      const fillId = pendingToolsRef.current.shift()
      if (fillId === undefined) return
      setFeed(prev => prev.map(item => {
        if (item.kind === 'tool' && item.id === fillId) {
          return {
            ...item,
            state: (event.has_error ? 'error' : 'done') as ToolState,
            result_preview: event.result_preview,
            has_error: event.has_error,
            error: event.error,
            latency_s: event.latency_s,
          }
        }
        return item
      }))
      return
    }

    if (event.type === 'tool_error') {
      const fillId = pendingToolsRef.current.shift()
      if (fillId !== undefined) {
        setFeed(prev => prev.map(item => {
          if (item.kind === 'tool' && item.id === fillId) {
            return { ...item, state: 'error' as ToolState, has_error: true, error: event.error }
          }
          return item
        }))
      }
      return
    }

    if (event.type === 'tools_ready') {
      pendingToolSchemasRef.current = event.tools
      return
    }

    if (event.type === 'prompt_ready') {
      setFeed(prev => [...prev, {
        kind: 'context_ready',
        id: itemIdRef.current++,
        messages: event.messages,
        tools: pendingToolSchemasRef.current,
      }])
      return
    }

    if (event.type === 'done') {
      setAnswer(event.answer)
      setRunState('done')
      stopTimer()
      closeStream()
      _enrichToolCards(event)
      return
    }

    if (event.type === 'error') {
      setErrorMsg(event.message + (event.detail ? ` — ${event.detail}` : ''))
      setRunState('error')
      stopTimer()
      closeStream()
    }
  }, [stopTimer, closeStream])

  // Post-run: annotate tool cards with LLM output and context slice from conversation_trace
  function _enrichToolCards(event: DoneEvent) {
    if (!event.conversation_trace || event.conversation_trace.length === 0) return
    setFeed(prev => {
      const trace: ConvTurn[] = event.conversation_trace
      const toolCards = prev.filter(f => f.kind === 'tool') as ToolFeedItem[]
      let toolIdx = 0
      for (let i = 0; i < trace.length; i++) {
        const turn = trace[i]
        if (turn.role === 'assistant' && turn.tool_calls && turn.tool_calls.length > 0) {
          const contextSlice = trace.slice(0, i)
          const assistantText = typeof turn.content === 'string' ? turn.content : ''
          for (const tc of turn.tool_calls) {
            if (toolIdx >= toolCards.length) break
            toolCards[toolIdx] = {
              ...toolCards[toolIdx],
              llm_output: assistantText,
              tool_call_def: JSON.stringify(tc, null, 2),
              context_slice: contextSlice,
            }
            toolIdx++
          }
        }
      }
      const enriched = new Map(toolCards.map(c => [c.id, c]))
      return prev.map(item => item.kind === 'tool' && enriched.has(item.id) ? enriched.get(item.id)! : item)
    })
  }

  const run = useCallback(() => {
    if (runState === 'running') return

    // Reset state
    setFeed([])
    setAnswer(null)
    setErrorMsg(null)
    setElapsed(0)
    itemIdRef.current = 0
    pendingToolsRef.current = []
    pendingToolSchemasRef.current = []
    setRunState('running')

    void (async () => {
      let jobId: string
      try {
        jobId = await startRun()
      } catch (e) {
        setErrorMsg(String(e))
        setRunState('error')
        return
      }

      const start = Date.now()
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - start) / 1000))
      }, 1000)

      const es = new EventSource(streamUrl(jobId))
      esRef.current = es

      es.onmessage = (e: MessageEvent<string>) => {
        try {
          const event = JSON.parse(e.data) as SSEEvent
          handleEvent(event)
        } catch {
          // ignore malformed JSON
        }
      }

      es.onerror = () => {
        setRunState(prev => {
          if (prev === 'running') {
            setErrorMsg('Connection to event stream dropped.')
            stopTimer()
            es.close()
            esRef.current = null
            return 'error'
          }
          return prev
        })
      }
    })()
  }, [runState, startRun, streamUrl, handleEvent, stopTimer])

  const clear = useCallback(() => {
    closeStream()
    setFeed([])
    setAnswer(null)
    setErrorMsg(null)
    setElapsed(0)
    itemIdRef.current = 0
    pendingToolsRef.current = []
    pendingToolSchemasRef.current = []
    setRunState('idle')
  }, [closeStream])

  // Cleanup on unmount
  useEffect(() => {
    return () => { closeStream() }
  }, [closeStream])

  return {
    feed,
    runState,
    elapsed,
    answer,
    errorMsg,
    isRunning: runState === 'running',
    run,
    clear,
  }
}
