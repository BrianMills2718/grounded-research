import { useState } from 'react'
import AgentFeed from '../AgentFeed/AgentFeed'
import { useAgentRun } from '../AgentFeed/useAgentRun'

const CONFIGS = ['standard', 'testing'] as const
type Config = (typeof CONFIGS)[number]

function phaseColor(tool: string): string {
  if (tool === 'decompose_question') return '#7c3aed'
  if (tool === 'collect_evidence')   return '#0891b2'
  if (tool === 'analyze')            return '#2563eb'
  if (tool === 'canonicalize')       return '#d97706'
  if (tool === 'adjudicate')         return '#db2777'
  if (tool === 'export')             return '#16a34a'
  return 'var(--accent)'
}

export default function AgentRunner() {
  const [question, setQuestion] = useState('')
  const [config, setConfig]     = useState<Config>('standard')

  const { feed, runState, elapsed, answer, errorMsg, isRunning, run, clear } = useAgentRun({
    startRun: async () => {
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim(), config }),
      })
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
      const data = await res.json() as { job_id: string }
      return data.job_id
    },
    streamUrl: (jobId) => `/api/stream/${jobId}`,
  })

  const labelStyle: React.CSSProperties = {
    fontSize: 11,
    color: 'var(--muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: 4,
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden', width: '100%' }}>
      {/* ── Left panel ── */}
      <div style={{
        width: 340,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid var(--border)',
        overflow: 'hidden',
        padding: 'var(--space-4)',
        gap: 'var(--space-3)',
      }}>
        <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text)', flexShrink: 0 }}>
          Grounded Research
        </div>

        {/* Research question */}
        <div style={{ flexShrink: 0 }}>
          <div style={labelStyle}>Research question</div>
          <textarea
            value={question}
            onChange={e => setQuestion(e.target.value)}
            rows={5}
            placeholder="e.g. What are the effects of social media on teen mental health?"
            style={{
              width: '100%',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              borderRadius: 4,
              padding: 'var(--space-2)',
              fontSize: 13,
              fontFamily: 'inherit',
              resize: 'vertical',
              minHeight: 88,
              boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Config profile */}
        <div style={{ flexShrink: 0 }}>
          <div style={labelStyle}>Config profile</div>
          <select
            value={config}
            onChange={e => setConfig(e.target.value as Config)}
            style={{
              width: '100%',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              borderRadius: 4,
              padding: 'var(--space-1) var(--space-2)',
              fontSize: 12,
            }}
          >
            <option value="standard">standard</option>
            <option value="testing">testing (cheap models)</option>
          </select>
        </div>

        {/* Run + Clear */}
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          <button
            className="primary"
            style={{ flex: 1, fontSize: 13, fontWeight: 600 }}
            disabled={isRunning || !question.trim()}
            onClick={run}
          >
            {isRunning ? 'Running…' : '▶ Run'}
          </button>
          <button style={{ fontSize: 13 }} disabled={isRunning} onClick={clear}>
            Clear
          </button>
        </div>

        {/* Running state */}
        {isRunning && (
          <div style={{
            flexShrink: 0,
            padding: 'var(--space-2) var(--space-3)',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 4,
            fontSize: 12,
            color: 'var(--running)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            <span style={{
              display: 'inline-block',
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: 'var(--running)',
              animation: 'runner-pulse 1.2s ease-in-out infinite',
              flexShrink: 0,
            }} />
            <span>Running — {elapsed}s elapsed</span>
          </div>
        )}

        {/* Error */}
        {runState === 'error' && errorMsg && (
          <div style={{
            flexShrink: 0,
            padding: 'var(--space-2) var(--space-3)',
            background: '#2a1010',
            border: '1px solid var(--error)',
            borderRadius: 4,
            fontSize: 12,
            color: 'var(--error)',
            lineHeight: 1.5,
          }}>
            <div style={{ fontWeight: 600, marginBottom: 3 }}>Run failed</div>
            {errorMsg}
          </div>
        )}

        {/* Answer / Executive recommendation */}
        {runState === 'done' && answer !== null && (
          <div style={{
            flexShrink: 0,
            padding: 'var(--space-3)',
            background: '#0d2b0d',
            border: '1px solid var(--done)',
            borderRadius: 4,
            overflowY: 'auto',
            maxHeight: 260,
          }}>
            <div style={{
              fontSize: 11,
              color: 'var(--done)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: 5,
            }}>
              Executive Recommendation
            </div>
            <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.6 }}>
              {answer || '(no recommendation)'}
            </div>
          </div>
        )}

        <div style={{ flex: 1 }} />
      </div>

      {/* ── Right panel: event feed ── */}
      <AgentFeed
        feed={feed}
        runState={runState}
        toolColorFn={phaseColor}
        emptyState={
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', height: '100%', gap: 8, color: 'var(--muted)',
          }}>
            <div style={{ fontSize: 32 }}>🔍</div>
            <div style={{ fontSize: 14 }}>Enter a research question and click Run</div>
            <div style={{ fontSize: 12 }}>
              Phases: decompose → collect → analyze → canonicalize → adjudicate → export
            </div>
          </div>
        }
      />
    </div>
  )
}
