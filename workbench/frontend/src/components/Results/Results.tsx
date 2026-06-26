import { useEffect, useState } from 'react'
import MarkdownViewer from '../MarkdownViewer/MarkdownViewer'
import JSONTreeViewer from '../JSONTreeViewer/JSONTreeViewer'
import ClaimLedgerViewer from '../ClaimLedgerViewer/ClaimLedgerViewer'

interface RunMeta {
  id: string
  dir: string
  question: string
  has_report: boolean
  mtime: number
}

export default function Results() {
  const [runs, setRuns] = useState<RunMeta[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [content, setContent] = useState<string | null>(null)
  const [traceData, setTraceData] = useState<unknown>(null)
  const [view, setView] = useState<'report' | 'trace' | 'claims'>('report')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function loadReport(id: string) {
    setSelectedId(id)
    setContent(null)
    setTraceData(null)
    setLoading(true)
    setError(null)
    setView('report')

    const reportFetch = fetch(`/api/runs/${id}/report`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then((d: { content: string }) => setContent(d.content))

    const traceFetch = fetch(`/api/runs/${id}/trace`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then((d: { data: unknown }) => setTraceData(d.data))
      .catch(() => {
        // Trace is optional — some runs may not have it yet
        setTraceData(null)
      })

    Promise.all([reportFetch, traceFetch])
      .catch(() => setError('Failed to load report'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetch('/api/runs')
      .then(r => r.json())
      .then((data: RunMeta[]) => {
        setRuns(data)
        // Auto-select first run with a report
        const first = data.find(r => r.has_report)
        if (first) loadReport(first.id)
      })
      .catch(() => setError('Failed to load runs'))
  }, [])

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Run list */}
      <div style={{
        width: 280, flexShrink: 0,
        borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <div style={{
          padding: 'var(--space-3) var(--space-4)',
          borderBottom: '1px solid var(--border)',
          fontSize: 11, fontWeight: 700, color: 'var(--muted)',
          textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0,
        }}>
          Past runs ({runs.filter(r => r.has_report).length})
        </div>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {runs.length === 0 && (
            <div style={{ padding: 'var(--space-4)', color: 'var(--muted)', fontSize: 13 }}>
              No completed runs yet
            </div>
          )}
          {runs.filter(r => r.has_report).map(run => (
            <button
              key={run.id}
              onClick={() => loadReport(run.id)}
              style={{
                width: '100%', textAlign: 'left',
                padding: 'var(--space-3) var(--space-4)',
                background: selectedId === run.id ? 'var(--surface)' : 'none',
                border: 'none',
                borderBottom: '1px solid var(--border)',
                borderLeft: selectedId === run.id ? '3px solid var(--accent)' : '3px solid transparent',
                cursor: 'pointer',
                color: 'var(--text)',
              }}
            >
              <div style={{ fontSize: 12, lineHeight: 1.4, color: 'var(--text)', marginBottom: 3 }}>
                {run.question.length > 60 ? run.question.slice(0, 60) + '…' : run.question}
              </div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                {new Date(run.mtime * 1000).toLocaleString()}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Right panel: toggle bar + content */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {/* View toggle — only show when a run is selected */}
        {selectedId !== null && !loading && (
          <div style={{
            display: 'flex', gap: 2,
            padding: 'var(--space-2) var(--space-4)',
            borderBottom: '1px solid var(--border)',
            flexShrink: 0,
            background: 'var(--surface)',
          }}>
            {(['report', 'trace', 'claims'] as const).map(v => (
              <button
                key={v}
                onClick={() => setView(v)}
                style={{
                  padding: 'var(--space-1) var(--space-3)',
                  fontSize: 11, fontWeight: 600,
                  textTransform: 'uppercase', letterSpacing: '0.05em',
                  background: view === v ? 'var(--accent)' : 'none',
                  color: view === v ? '#fff' : 'var(--muted)',
                  border: '1px solid ' + (view === v ? 'var(--accent)' : 'var(--border)'),
                  borderRadius: 3, cursor: 'pointer',
                }}
              >
                {v}
              </button>
            ))}
          </div>
        )}

        {loading && (
          <div style={{ padding: 'var(--space-5)', color: 'var(--muted)', fontSize: 13 }}>
            Loading…
          </div>
        )}
        {error && (
          <div style={{ padding: 'var(--space-4)', color: 'var(--error)', fontSize: 13 }}>
            {error}
          </div>
        )}
        {!loading && !error && selectedId === null && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            height: '100%', color: 'var(--muted)', fontSize: 13,
          }}>
            Select a run to view its report
          </div>
        )}

        {/* Report view */}
        {!loading && view === 'report' && content !== null && (
          <div style={{ overflow: 'auto', flex: 1, padding: 'var(--space-5)' }}>
            <MarkdownViewer content={content} />
          </div>
        )}

        {/* Trace view */}
        {!loading && view === 'trace' && (
          <div style={{ overflow: 'auto', flex: 1, padding: 'var(--space-4)' }}>
            {traceData !== null
              ? <JSONTreeViewer data={traceData} collapsed={2} />
              : (
                <div style={{ color: 'var(--muted)', fontSize: 13 }}>
                  No trace data available for this run
                </div>
              )
            }
          </div>
        )}

        {/* Claims view */}
        {!loading && view === 'claims' && (() => {
          type TracePayload = {
            stage_5_verification_result?: {
              updated_claim_ledger?: unknown[]
              updated_dispute_queue?: unknown[]
            }
            stage_6_synthesis_report?: {
              disagreement_map?: unknown[]
            }
          }
          const payload = traceData as TracePayload | null
          const claims = (payload?.stage_5_verification_result?.updated_claim_ledger ?? []) as Parameters<typeof ClaimLedgerViewer>[0]['claims']
          const disputes = (payload?.stage_5_verification_result?.updated_dispute_queue ?? []) as Parameters<typeof ClaimLedgerViewer>[0]['disputes']
          const resolutions = (payload?.stage_6_synthesis_report?.disagreement_map ?? []) as Parameters<typeof ClaimLedgerViewer>[0]['resolutions']

          if (claims.length === 0) {
            return (
              <div style={{ padding: 'var(--space-5)', color: 'var(--muted)', fontSize: 13 }}>
                No claim data available — this run may not have completed Stage 5
              </div>
            )
          }
          return (
            <div style={{ overflow: 'hidden', flex: 1 }}>
              <ClaimLedgerViewer claims={claims} disputes={disputes} resolutions={resolutions} />
            </div>
          )
        })()}
      </div>
    </div>
  )
}
