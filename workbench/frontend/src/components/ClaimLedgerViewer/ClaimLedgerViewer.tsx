/**
 * ClaimLedgerViewer — two-panel view of the claim ledger and dispute queue
 * produced by grounded-research Stage 5.
 *
 * Left panel (55%): claims table with status badges and selection.
 * Right panel (45%): disputes + inline resolutions, highlighted when a claim
 * is selected.
 *
 * Uses inline styles + CSS custom properties for theming. No CSS modules.
 */

import { useState } from 'react'

export interface Claim {
  id: string
  statement: string
  status: 'supported' | 'contested' | 'verified' | string
  source_references: string[]
  is_provisional: boolean
  evidence_label: string
  related_assumptions: string[]
}

export interface Dispute {
  id: string
  type: 'interpretive' | 'empirical' | 'spec_ambiguity' | string
  description: string
  claims_involved: string[]
  decision_critical: boolean
  status: 'resolved' | 'unresolved' | string
  resolution_routing?: string
}

export interface DisputeResolution {
  dispute_id: string
  type: string
  summary: string
  resolution: string
  action_taken: string
  chosen_interpretation: string
}

interface Props {
  claims: Claim[]
  disputes: Dispute[]
  resolutions: DisputeResolution[]
}

// ── colour helpers ────────────────────────────────────────────────────────────

function statusColor(status: string): string {
  switch (status) {
    case 'verified':  return 'var(--done, #16a34a)'
    case 'supported': return 'var(--accent, #2563eb)'
    case 'contested': return '#d97706'
    default:          return 'var(--muted, #6b7280)'
  }
}

function disputeTypeColor(type: string): string {
  switch (type) {
    case 'interpretive':   return '#7c3aed'
    case 'empirical':      return 'var(--accent, #2563eb)'
    case 'spec_ambiguity': return 'var(--muted, #6b7280)'
    default:               return 'var(--muted, #6b7280)'
  }
}

// ── small reusable badge ──────────────────────────────────────────────────────

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      display: 'inline-block',
      padding: '1px 6px',
      borderRadius: 3,
      fontSize: 10,
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
      background: color + '22',
      color,
      border: `1px solid ${color}44`,
      whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  )
}

// ── summary line ─────────────────────────────────────────────────────────────

function ClaimSummary({ claims }: { claims: Claim[] }) {
  const counts: Record<string, number> = {}
  for (const c of claims) counts[c.status] = (counts[c.status] ?? 0) + 1

  const parts: JSX.Element[] = []
  for (const [status, n] of Object.entries(counts)) {
    parts.push(
      <span key={status} style={{ color: statusColor(status) }}>
        {n} {status}
      </span>
    )
  }

  return (
    <span style={{ fontSize: 12, color: 'var(--muted)' }}>
      {claims.length} claims:{' '}
      {parts.reduce<JSX.Element[]>((acc, el, i) =>
        i === 0 ? [el] : [...acc, <span key={`sep-${i}`} style={{ color: 'var(--muted)' }}> · </span>, el],
        []
      )}
    </span>
  )
}

// ── claims panel ─────────────────────────────────────────────────────────────

function ClaimsPanel({
  claims,
  selectedId,
  onSelect,
}: {
  claims: Claim[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  return (
    <div style={{
      width: '55%',
      borderRight: '1px solid var(--border, #e5e7eb)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 14px',
        borderBottom: '1px solid var(--border, #e5e7eb)',
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Claims
        </span>
        <ClaimSummary claims={claims} />
      </div>

      {/* Table header */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '44px 1fr 74px 90px 36px',
        gap: 6,
        padding: '5px 14px',
        borderBottom: '1px solid var(--border, #e5e7eb)',
        fontSize: 10,
        fontWeight: 700,
        color: 'var(--muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        flexShrink: 0,
        background: 'var(--surface, #f9fafb)',
      }}>
        <div>ID</div>
        <div>Statement</div>
        <div>Status</div>
        <div>Evidence</div>
        <div style={{ textAlign: 'right' }}>Srcs</div>
      </div>

      {/* Rows */}
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {claims.map(claim => {
          const isSelected = claim.id === selectedId
          return (
            <div
              key={claim.id}
              onClick={() => onSelect(claim.id)}
              title={claim.statement}
              style={{
                display: 'grid',
                gridTemplateColumns: '44px 1fr 74px 90px 36px',
                gap: 6,
                padding: '7px 14px',
                borderBottom: '1px solid var(--border, #e5e7eb)',
                borderLeft: isSelected
                  ? '3px solid var(--accent, #2563eb)'
                  : '3px solid transparent',
                background: isSelected ? 'var(--surface, #f9fafb)' : 'none',
                cursor: 'pointer',
                alignItems: 'start',
              }}
            >
              {/* ID */}
              <div style={{
                fontFamily: 'monospace',
                fontSize: 11,
                fontWeight: 700,
                color: 'var(--accent, #2563eb)',
                paddingTop: 1,
                whiteSpace: 'nowrap',
              }}>
                {claim.id}
              </div>

              {/* Statement — 2 lines max */}
              <div style={{
                fontSize: 12,
                lineHeight: 1.45,
                color: 'var(--text, #111827)',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}>
                {claim.statement}
              </div>

              {/* Status badge */}
              <div>
                <Badge label={claim.status} color={statusColor(claim.status)} />
                {claim.is_provisional && (
                  <span style={{ fontSize: 9, color: 'var(--muted)', display: 'block', marginTop: 2 }}>
                    provisional
                  </span>
                )}
              </div>

              {/* Evidence label */}
              <div style={{
                fontSize: 11,
                color: 'var(--muted)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {claim.evidence_label}
              </div>

              {/* Source count */}
              <div style={{
                fontSize: 11,
                color: 'var(--muted)',
                textAlign: 'right',
                fontVariantNumeric: 'tabular-nums',
              }}>
                {claim.source_references.length}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── disputes panel ────────────────────────────────────────────────────────────

function DisputeCard({
  dispute,
  resolution,
  highlighted,
}: {
  dispute: Dispute
  resolution: DisputeResolution | undefined
  highlighted: boolean
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div style={{
      borderBottom: '1px solid var(--border, #e5e7eb)',
      padding: '10px 14px',
      background: highlighted ? 'var(--surface, #f9fafb)' : 'none',
      borderLeft: highlighted ? '3px solid #7c3aed' : '3px solid transparent',
    }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 5 }}>
        <span style={{
          fontFamily: 'monospace',
          fontSize: 11,
          fontWeight: 700,
          color: 'var(--text, #111827)',
          whiteSpace: 'nowrap',
        }}>
          [{dispute.id}]
        </span>
        <Badge label={dispute.type} color={disputeTypeColor(dispute.type)} />
        {dispute.decision_critical && (
          <span title="Decision critical" style={{ fontSize: 13, color: '#d97706' }}>★</span>
        )}
        <div style={{ marginLeft: 'auto' }}>
          <Badge
            label={dispute.status}
            color={dispute.status === 'resolved' ? 'var(--done, #16a34a)' : '#d97706'}
          />
        </div>
      </div>

      {/* Description */}
      <div style={{
        fontSize: 12,
        lineHeight: 1.45,
        color: 'var(--text, #111827)',
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
        marginBottom: 5,
      }}>
        {dispute.description}
      </div>

      {/* Claims involved */}
      {dispute.claims_involved.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 5 }}>
          {dispute.claims_involved.map(cid => (
            <span key={cid} style={{
              fontFamily: 'monospace',
              fontSize: 10,
              padding: '1px 5px',
              borderRadius: 3,
              background: 'var(--accent, #2563eb)22',
              color: 'var(--accent, #2563eb)',
              border: '1px solid var(--accent, #2563eb)44',
            }}>
              {cid}
            </span>
          ))}
        </div>
      )}

      {/* Resolution section (only when resolved) */}
      {dispute.status === 'resolved' && resolution && (
        <div>
          <button
            onClick={() => setExpanded(e => !e)}
            style={{
              fontSize: 10,
              fontWeight: 600,
              color: 'var(--accent, #2563eb)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 0,
              textDecoration: 'underline',
            }}
          >
            {expanded ? '▲ hide resolution' : '▼ show resolution'}
          </button>
          {expanded && (
            <div style={{
              marginTop: 6,
              padding: '8px 10px',
              background: 'var(--done, #16a34a)11',
              border: '1px solid var(--done, #16a34a)33',
              borderRadius: 4,
              fontSize: 11,
              lineHeight: 1.5,
              color: 'var(--text, #111827)',
            }}>
              <div style={{ marginBottom: 4 }}>
                <strong style={{ color: 'var(--muted)' }}>Resolution: </strong>
                {resolution.resolution}
              </div>
              <div>
                <strong style={{ color: 'var(--muted)' }}>Interpretation: </strong>
                {resolution.chosen_interpretation}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function DisputesPanel({
  disputes,
  resolutions,
  selectedClaimId,
}: {
  disputes: Dispute[]
  resolutions: DisputeResolution[]
  selectedClaimId: string | null
}) {
  const resolutionMap = Object.fromEntries(
    resolutions.map(r => [r.dispute_id, r])
  )

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        padding: '10px 14px',
        borderBottom: '1px solid var(--border, #e5e7eb)',
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Disputes
        </span>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>
          {disputes.length} total
        </span>
      </div>

      {/* Dispute cards */}
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {disputes.length === 0 && (
          <div style={{ padding: 14, color: 'var(--muted)', fontSize: 13 }}>
            No disputes recorded
          </div>
        )}
        {disputes.map(dispute => (
          <DisputeCard
            key={dispute.id}
            dispute={dispute}
            resolution={resolutionMap[dispute.id]}
            highlighted={
              selectedClaimId !== null &&
              dispute.claims_involved.includes(selectedClaimId)
            }
          />
        ))}
      </div>
    </div>
  )
}

// ── root export ───────────────────────────────────────────────────────────────

export default function ClaimLedgerViewer({ claims, disputes, resolutions }: Props) {
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null)

  function handleSelect(id: string) {
    setSelectedClaimId(prev => (prev === id ? null : id))
  }

  return (
    <div style={{
      display: 'flex',
      height: '100%',
      overflow: 'hidden',
      fontSize: 13,
    }}>
      <ClaimsPanel
        claims={claims}
        selectedId={selectedClaimId}
        onSelect={handleSelect}
      />
      <DisputesPanel
        disputes={disputes}
        resolutions={resolutions}
        selectedClaimId={selectedClaimId}
      />
    </div>
  )
}
