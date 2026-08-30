import {
  AlertTriangle,
  Box,
  CheckCircle2,
  CircleDot,
  FileKey2,
  Globe2,
  Hash,
  Network,
  Server,
} from 'lucide-react'

import type { Entity } from '../types'

export function LogoMark({ size = 34 }: { size?: number }) {
  return (
    <svg className="logo-mark" width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <path d="M8 11.5 20 5l12 6.5v17L20 35 8 28.5z" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <circle cx="20" cy="12" r="2.5" fill="currentColor" />
      <circle cx="13" cy="25" r="2.5" fill="currentColor" />
      <circle cx="28" cy="26" r="2.5" fill="currentColor" />
      <path d="m20 14.5-6 8.3m8.3-8.5 4.3 9.3M15.5 25h10" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  )
}

export function Loading({ label = 'Loading intelligence' }: { label?: string }) {
  return (
    <div className="loading-state">
      <span className="radar-loader" />
      <span>{label}</span>
    </div>
  )
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="empty-state">
      <CircleDot size={25} />
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  )
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="error-banner" role="alert">
      <AlertTriangle size={17} />
      {message}
    </div>
  )
}

export function EntityIcon({ type, size = 16 }: { type: string; size?: number }) {
  if (['domain', 'hostname', 'url'].includes(type)) return <Globe2 size={size} />
  if (type === 'ip_address') return <Server size={size} />
  if (type === 'file_hash') return <Hash size={size} />
  if (type === 'certificate') return <FileKey2 size={size} />
  if (type === 'asn' || type === 'infrastructure') return <Network size={size} />
  return <Box size={size} />
}

export function RiskBadge({ score }: { score: number }) {
  const level = score >= 70 ? 'critical' : score >= 40 ? 'elevated' : score > 0 ? 'guarded' : 'neutral'
  return (
    <span className={`risk-badge risk-${level}`} title={`Risk score ${score} out of 100`}>
      {score}
    </span>
  )
}

export function StatusPill({ value }: { value: string }) {
  const positive = ['completed', 'healthy', 'enabled', 'closed'].includes(value)
  const warning = ['partial', 'failed', 'critical'].includes(value)
  return (
    <span className={`status-pill ${positive ? 'positive' : warning ? 'warning' : ''}`}>
      {positive && <CheckCircle2 size={11} />}
      {value.replaceAll('_', ' ')}
    </span>
  )
}

export function formatDate(value?: string): string {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export function friendlyType(value: string): string {
  return value.replaceAll('_', ' ')
}

export function EntityTable({ entities, onSelect }: { entities: Entity[]; onSelect?: (item: Entity) => void }) {
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Observable</th>
            <th>Type</th>
            <th>Classification</th>
            <th>Confidence</th>
            <th>Risk</th>
            <th>Last seen</th>
          </tr>
        </thead>
        <tbody>
          {entities.map((entity) => (
            <tr key={entity.id} onClick={() => onSelect?.(entity)} className={onSelect ? 'clickable' : ''}>
              <td>
                <div className="observable-cell">
                  <span className="entity-icon"><EntityIcon type={entity.type} /></span>
                  <div>
                    <strong>{entity.display_name || entity.value}</strong>
                    <small>{entity.tags.map((tag) => `#${tag.name}`).join(' ') || 'untagged'}</small>
                  </div>
                </div>
              </td>
              <td className="muted">{friendlyType(entity.type)}</td>
              <td><span className={`classification classification-${entity.classification}`}>{entity.classification}</span></td>
              <td>{entity.confidence}%</td>
              <td><RiskBadge score={entity.risk_score} /></td>
              <td className="muted">{formatDate(entity.last_seen)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
