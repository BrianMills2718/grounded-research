// Standard SSE event types for agent runner UIs.
// These mirror the Python models in python/ui_protocol/events.py.
// Keep both sides in sync when adding new event types.

// ── Inbound SSE event types ───────────────────────────────────────────────────

export interface StatusEvent {
  type: 'status'
  message: string
  seq: number
}

export interface ToolStartEvent {
  type: 'tool_start'
  tool: string
  tool_reasoning: string
  args: Record<string, unknown>
  seq: number
}

export interface ToolEndEvent {
  type: 'tool_end'
  tool: string
  result_preview: string
  has_error: boolean
  error: string
  latency_s: number
  seq: number
}

export interface ToolErrorEvent {
  type: 'tool_error'
  tool: string
  error: string
  seq: number
}

export interface HeartbeatEvent {
  type: 'heartbeat'
}

export interface ToolsReadyEvent {
  type: 'tools_ready'
  tools: Array<{ name: string; description: string; parameters: Record<string, unknown> }>
  seq: number
}

export interface PromptReadyEvent {
  type: 'prompt_ready'
  messages: Array<{ role: string; content: string | null }>
  seq: number
}

export interface ConvTurn {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string | null
  tool_calls?: Array<{ id: string; type: string; function: { name: string; arguments: string } }>
  tool_call_id?: string
  name?: string
}

export interface DoneEvent {
  type: 'done'
  answer: string
  finish_reason: string
  num_turns: number
  n_tool_calls: number
  elapsed_s: number
  tool_details: unknown[]
  conversation_trace: ConvTurn[]
  seq: number
}

export interface ErrorEvent {
  type: 'error'
  message: string
  detail: string
}

export type SSEEvent =
  | StatusEvent
  | ToolStartEvent
  | ToolEndEvent
  | ToolErrorEvent
  | HeartbeatEvent
  | ToolsReadyEvent
  | PromptReadyEvent
  | DoneEvent
  | ErrorEvent

// ── Feed item types (rendered in AgentFeed) ───────────────────────────────────

export interface StatusFeedItem {
  kind: 'status'
  id: number
  message: string
}

export interface ContextReadyFeedItem {
  kind: 'context_ready'
  id: number
  messages: Array<{ role: string; content: string | null }>
  tools: Array<{ name: string; description: string; parameters: Record<string, unknown> }>
}

export type ToolState = 'pending' | 'done' | 'error'

export interface ToolFeedItem {
  kind: 'tool'
  id: number
  tool: string
  tool_reasoning: string
  args: Record<string, unknown>
  state: ToolState
  result_preview: string
  has_error: boolean
  error: string
  latency_s: number | null
  // Populated after run completes from conversation_trace
  llm_output?: string
  tool_call_def?: string
  context_slice?: ConvTurn[]
}

export type FeedItem = StatusFeedItem | ContextReadyFeedItem | ToolFeedItem

export type RunState = 'idle' | 'running' | 'done' | 'error'
