import { useEffect, useState } from 'react'
import MarkdownViewer from '../MarkdownViewer/MarkdownViewer'

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
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function loadReport(id: string) {
    setSelectedId(id)
    setContent(null)
    setLoading(true)
    setError(null)
    fetch(`/api/runs/${id}/report`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then((d: { content: string }) => setContent(d.content))
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

      {/* Report viewer */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {loading && (
          <div style={{ padding: 'var(--space-5)', color: 'var(--muted)', fontSize: 13 }}>
            Loading report…
          </div>
        )}
        {error && (
          <div style={{ padding: 'var(--space-4)', color: 'var(--error)', fontSize: 13 }}>
            {error}
          </div>
        )}
        {!loading && !error && content === null && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            height: '100%', color: 'var(--muted)', fontSize: 13,
          }}>
            Select a run to view its report
          </div>
        )}
        {!loading && content !== null && (
          <div style={{ overflow: 'auto', flex: 1, padding: 'var(--space-5)' }}>
            <MarkdownViewer content={content} />
          </div>
        )}
      </div>
    </div>
  )
}
