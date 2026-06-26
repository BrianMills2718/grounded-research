import { useState } from 'react'
import AgentRunner from './components/AgentRunner/AgentRunner'

type Tab = 'runner' | 'config' | 'results'

const TABS: { id: Tab; label: string }[] = [
  { id: 'runner',  label: 'Runner'  },
  { id: 'config',  label: 'Config'  },
  { id: 'results', label: 'Results' },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('runner')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <nav style={{
        display: 'flex',
        gap: 2,
        padding: '0 var(--space-3)',
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          paddingRight: 'var(--space-4)',
          fontWeight: 700,
          fontSize: 13,
          color: 'var(--muted)',
          letterSpacing: '-0.01em',
        }}>
          Grounded Research
        </div>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: 'var(--space-2) var(--space-4)',
              background: 'none',
              border: 'none',
              borderBottom: tab === t.id
                ? '2px solid var(--accent)'
                : '2px solid transparent',
              color: tab === t.id ? 'var(--accent)' : 'var(--muted)',
              borderRadius: 0,
              fontWeight: tab === t.id ? 600 : 400,
              cursor: 'pointer',
              fontSize: 'var(--text-base)',
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {tab === 'runner'  && <AgentRunner />}
        {tab === 'config'  && <Placeholder label="Config — edit ~/projects/grounded-research/config/config.yaml directly" />}
        {tab === 'results' && <Placeholder label="Results — check ~/projects/grounded-research/output/" />}
      </main>
    </div>
  )
}

function Placeholder({ label }: { label: string }) {
  return (
    <div style={{
      color: 'var(--muted)',
      fontSize: 'var(--text-sm)',
      padding: 'var(--space-5)',
      margin: 'var(--space-5)',
      border: '1px dashed var(--border)',
      borderRadius: 'var(--radius-md)',
      textAlign: 'center',
    }}>
      {label}
    </div>
  )
}
