import { useEffect, useRef } from 'react'
import type { FeedItem, RunState } from './sse-events'
import { ContextReadyCard, ToolCallCard } from './ToolCallCard'
import './AgentFeed.css'

interface AgentFeedProps {
  feed: FeedItem[]
  runState: RunState
  toolColorFn?: (tool: string) => string
  emptyState?: React.ReactNode
}

export default function AgentFeed({ feed, runState, toolColorFn, emptyState }: AgentFeedProps) {
  const feedRef = useRef<HTMLDivElement>(null)

  // Auto-scroll only when near the bottom (within 120px), so reading mid-feed isn't disrupted
  useEffect(() => {
    const el = feedRef.current
    if (!el) return
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120
    if (nearBottom) el.scrollTop = el.scrollHeight
  }, [feed])

  const defaultEmpty = (
    <div style={{
      minHeight: 200, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 8, color: 'var(--muted)',
    }}>
      <div style={{ fontSize: 32 }}>&#x26a1;</div>
      <div style={{ fontSize: 14 }}>Start a run to see a live agent trace</div>
    </div>
  )

  return (
    <div ref={feedRef} className="agent-feed">
      {feed.length === 0 && runState === 'idle' && (emptyState ?? defaultEmpty)}

      {feed.map(item => {
        if (item.kind === 'status') {
          return (
            <div key={item.id} style={{
              fontSize: 12, color: 'var(--muted)', padding: '3px 4px',
              marginBottom: 4, fontStyle: 'italic',
            }}>
              {item.message}
            </div>
          )
        }
        if (item.kind === 'context_ready') {
          return <ContextReadyCard key={item.id} item={item} />
        }
        return <ToolCallCard key={item.id} item={item} toolColorFn={toolColorFn} />
      })}
    </div>
  )
}
