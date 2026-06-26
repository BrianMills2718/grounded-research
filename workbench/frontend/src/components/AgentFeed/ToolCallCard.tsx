import { useState } from 'react'
import type { ContextReadyFeedItem, ConvTurn, ToolFeedItem } from './sse-events'

// ── SubSection — collapsible detail block inside ToolCallCard ─────────────────

function SubSection({ label, children }: { label: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ marginTop: 8 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          background: 'none', border: 'none', cursor: 'pointer', padding: '3px 0',
          color: 'var(--accent)', fontSize: 11, fontWeight: 600,
          display: 'flex', alignItems: 'center', gap: 4,
        }}
      >
        <span style={{ fontSize: 9 }}>{open ? '▼' : '▶'}</span>
        {label}
      </button>
      {open && <div style={{ marginTop: 4 }}>{children}</div>}
    </div>
  )
}

// ── ToolCallCard ──────────────────────────────────────────────────────────────

interface ToolCallCardProps {
  item: ToolFeedItem
  toolColorFn?: (tool: string) => string
}

export function ToolCallCard({ item, toolColorFn }: ToolCallCardProps) {
  const [open, setOpen] = useState(false)
  const color = item.has_error
    ? 'var(--error)'
    : (toolColorFn ? toolColorFn(item.tool) : 'var(--accent)')

  const stateIcon =
    item.state === 'pending' ? (
      <span style={{
        display: 'inline-block', width: 14, height: 14, borderRadius: '50%',
        border: '2px solid var(--muted)', borderTopColor: 'var(--accent)',
        animation: 'runner-spin 0.8s linear infinite',
      }} />
    ) : item.state === 'error' || item.has_error ? (
      <span style={{ color: 'var(--error)', fontSize: 12, fontWeight: 700 }}>&#x2715;</span>
    ) : (
      <span style={{ color: 'var(--done)', fontSize: 12, fontWeight: 700 }}>&#x2713;</span>
    )

  return (
    <div style={{
      border: `1px solid ${item.has_error ? 'var(--error)' : 'var(--border)'}`,
      borderRadius: 6, marginBottom: 6, overflow: 'hidden',
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 8,
          padding: '7px 10px',
          background: item.has_error ? '#2a1010' : 'var(--surface)',
          border: 'none', cursor: 'pointer', textAlign: 'left',
        }}
      >
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color, minWidth: 160, flexShrink: 0 }}>
          {item.tool}
        </span>
        {item.latency_s !== null && (
          <span style={{
            background: 'var(--surface2)', border: '1px solid var(--border)',
            borderRadius: 3, fontSize: 11, padding: '1px 5px', color: 'var(--muted)', flexShrink: 0,
          }}>{item.latency_s.toFixed(2)}s</span>
        )}
        <span style={{ flex: 1 }} />
        <span style={{ flexShrink: 0, display: 'flex', alignItems: 'center' }}>{stateIcon}</span>
        <span style={{ color: 'var(--muted)', fontSize: 11, marginLeft: 4, flexShrink: 0 }}>{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div style={{ padding: '8px 10px', borderTop: '1px solid var(--border)', background: 'var(--bg)' }}>
          {item.tool_reasoning && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 3 }}>Reasoning</div>
              <div style={{ fontSize: 12, color: 'var(--muted)', fontStyle: 'italic', lineHeight: 1.5 }}>{item.tool_reasoning}</div>
            </div>
          )}

          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 3 }}>Arguments</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text)' }}>
              {Object.entries(item.args).map(([k, v]) => (
                <div key={k} style={{ marginBottom: 2 }}>
                  <span style={{ color: 'var(--muted)' }}>{k}: </span>
                  <span>{typeof v === 'string' ? v : JSON.stringify(v)}</span>
                </div>
              ))}
            </div>
          </div>

          {item.state !== 'pending' && (
            <div>
              <div style={{
                fontSize: 11, color: item.has_error ? 'var(--error)' : 'var(--muted)',
                textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 3,
              }}>
                {item.has_error ? 'Error' : 'Result'}
              </div>
              <pre style={{
                fontSize: 11, fontFamily: 'var(--font-mono)',
                background: 'var(--surface)',
                border: `1px solid ${item.has_error ? 'var(--error)' : 'var(--border)'}`,
                borderRadius: 4, padding: 8, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                color: item.has_error ? 'var(--error)' : 'var(--text)',
                maxHeight: 200, overflowY: 'auto', margin: 0,
              }}>
                {item.has_error ? item.error : item.result_preview}
              </pre>
            </div>
          )}

          <SubSection label="LLM output (this turn)">
            {item.llm_output !== undefined ? (
              item.tool_call_def !== undefined ? (
                <div>
                  {item.llm_output && (
                    <pre style={{
                      fontSize: 11, fontFamily: 'var(--font-mono)', background: 'var(--surface)',
                      border: '1px solid var(--border)', borderRadius: 4, padding: 8,
                      whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 160,
                      overflowY: 'auto', margin: '0 0 6px 0', color: 'var(--text)',
                    }}>{item.llm_output}</pre>
                  )}
                  <pre style={{
                    fontSize: 11, fontFamily: 'var(--font-mono)', background: 'var(--surface)',
                    border: '1px solid var(--border)', borderRadius: 4, padding: 8,
                    whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 200,
                    overflowY: 'auto', margin: 0, color: '#a5b4fc',
                  }}>{item.tool_call_def}</pre>
                </div>
              ) : <span style={{ fontSize: 11, color: 'var(--muted)' }}>(no text output in this turn)</span>
            ) : (
              <span style={{ fontSize: 11, color: 'var(--muted)', fontStyle: 'italic' }}>Available after run completes</span>
            )}
          </SubSection>

          <SubSection label="LLM context (all messages before this call)">
            {item.context_slice !== undefined ? (
              <div style={{ maxHeight: 300, overflowY: 'auto', border: '1px solid var(--border)', borderRadius: 4 }}>
                {item.context_slice.map((turn: ConvTurn, i: number) => (
                  <div key={i} style={{ borderBottom: '1px solid var(--border)', padding: '5px 8px' }}>
                    <span style={{
                      fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 600,
                      color: turn.role === 'assistant' ? 'var(--accent)'
                        : turn.role === 'system' ? '#f59e0b'
                        : turn.role === 'tool' ? '#16a34a'
                        : 'var(--muted)',
                    }}>
                      {turn.role.toUpperCase()}{turn.name ? ` (${turn.name})` : ''}
                    </span>
                    <pre style={{
                      fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text)',
                      whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: '3px 0 0 0',
                      maxHeight: 120, overflowY: 'auto',
                    }}>
                      {typeof turn.content === 'string' ? turn.content : JSON.stringify(turn.content, null, 2)}
                      {turn.tool_calls && turn.tool_calls.length > 0
                        && `\n[tool_calls: ${turn.tool_calls.map(tc => tc.function.name).join(', ')}]`}
                    </pre>
                  </div>
                ))}
              </div>
            ) : (
              <span style={{ fontSize: 11, color: 'var(--muted)', fontStyle: 'italic' }}>Available after run completes</span>
            )}
          </SubSection>
        </div>
      )}
    </div>
  )
}

// ── ContextReadyCard — initial agent context (messages + tool schemas) ────────

interface ContextReadyCardProps {
  item: ContextReadyFeedItem
}

export function ContextReadyCard({ item }: ContextReadyCardProps) {
  const [open, setOpen] = useState(false)
  const [section, setSection] = useState<'messages' | 'tools'>('messages')
  const [expandedTool, setExpandedTool] = useState<string | null>(null)

  const roleColor = (r: string) =>
    r === 'system' ? '#f59e0b' : r === 'assistant' ? 'var(--accent)' : r === 'tool' ? '#16a34a' : 'var(--muted)'

  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 6, marginBottom: 6 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px',
          background: 'var(--surface)', border: 'none', cursor: 'pointer', textAlign: 'left',
          borderRadius: open ? '6px 6px 0 0' : 6,
        }}
      >
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b', flexShrink: 0 }} />
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: '#f59e0b' }}>
          Agent context — {item.messages.length} messages + {item.tools.length} tools
        </span>
        <span style={{ flex: 1 }} />
        <span style={{ color: 'var(--muted)', fontSize: 11 }}>{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div style={{ borderTop: '1px solid var(--border)', background: 'var(--bg)' }}>
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border)' }}>
            {(['messages', 'tools'] as const).map(s => (
              <button key={s} onClick={() => setSection(s)} style={{
                padding: '5px 14px', fontSize: 11, fontWeight: section === s ? 600 : 400,
                color: section === s ? 'var(--text)' : 'var(--muted)',
                background: 'none', border: 'none',
                borderBottom: section === s ? '2px solid var(--accent)' : '2px solid transparent',
                cursor: 'pointer', textTransform: 'capitalize',
              }}>
                {s === 'messages' ? `Messages (${item.messages.length})` : `Tools (${item.tools.length})`}
              </button>
            ))}
          </div>

          {section === 'messages' && (
            <div style={{ maxHeight: 500, overflowY: 'auto' }}>
              {item.messages.map((msg, i) => (
                <div key={i} style={{ borderBottom: '1px solid var(--border)', padding: '6px 10px' }}>
                  <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 600, color: roleColor(msg.role) }}>
                    {msg.role.toUpperCase()}
                  </span>
                  <pre style={{
                    margin: '3px 0 0', fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text)',
                    whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 350, overflowY: 'auto',
                  }}>
                    {typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}

          {section === 'tools' && (
            <div style={{ maxHeight: 500, overflowY: 'auto' }}>
              {item.tools.map(t => (
                <div key={t.name} style={{ borderBottom: '1px solid var(--border)' }}>
                  <button
                    onClick={() => setExpandedTool(expandedTool === t.name ? null : t.name)}
                    style={{
                      width: '100%', display: 'flex', gap: 8, padding: '6px 10px',
                      background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', alignItems: 'flex-start',
                    }}
                  >
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: 'var(--accent)', minWidth: 160, flexShrink: 0 }}>
                      {t.name}
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--muted)', lineHeight: 1.4, flex: 1 }}>
                      {t.description.slice(0, 100)}{t.description.length > 100 ? '…' : ''}
                    </span>
                    <span style={{ color: 'var(--muted)', fontSize: 10, flexShrink: 0 }}>
                      {expandedTool === t.name ? '▲' : '▼'}
                    </span>
                  </button>
                  {expandedTool === t.name && (
                    <pre style={{
                      margin: 0, padding: '4px 10px 8px', fontSize: 10, fontFamily: 'var(--font-mono)',
                      color: 'var(--text)', background: '#0a0a0f', whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word', maxHeight: 300, overflowY: 'auto',
                      borderTop: '1px solid var(--border)',
                    }}>
                      {JSON.stringify(t.parameters, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
