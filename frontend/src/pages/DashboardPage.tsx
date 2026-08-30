import {
  Activity,
  ArrowRight,
  BriefcaseBusiness,
  Database,
  Network,
  Plus,
  RadioTower,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api'
import { EmptyState, EntityIcon, ErrorBanner, formatDate, Loading, RiskBadge, StatusPill, friendlyType } from '../components/Common'
import type { DashboardData } from '../types'

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api<DashboardData>('/dashboard').then(setData).catch((caught) => setError(caught.message))
  }, [])

  if (error) return <ErrorBanner message={error} />
  if (!data) return <Loading />
  const maxType = Math.max(...Object.values(data.entities_by_type), 1)

  return (
    <div className="page-stack">
      <section className="page-heading">
        <div><span className="eyebrow">LIVE WORKSPACE</span><h1>Intelligence overview</h1><p>A defensible view of what you know, where it came from, and what deserves attention.</p></div>
        <button className="primary-button" onClick={() => navigate('/intelligence?new=1')}><Plus size={16} />Add observable</button>
      </section>

      <section className="metric-grid">
        <article className="metric-card"><span className="metric-icon mint"><Database size={18} /></span><div><small>Known entities</small><strong>{data.entity_total.toLocaleString()}</strong><span>normalized & deduplicated</span></div></article>
        <article className="metric-card"><span className="metric-icon blue"><Network size={18} /></span><div><small>Relationships</small><strong>{data.relationship_total.toLocaleString()}</strong><span>provenance preserved</span></div></article>
        <article className="metric-card"><span className="metric-icon violet"><BriefcaseBusiness size={18} /></span><div><small>Investigations</small><strong>{data.investigation_total}</strong><span>across all states</span></div></article>
        <article className="metric-card alert"><span className="metric-icon coral"><ShieldAlert size={18} /></span><div><small>High-risk entities</small><strong>{data.high_risk_total}</strong><span>score ≥ 50 · explained</span></div></article>
      </section>

      <section className="dashboard-grid">
        <article className="panel span-two">
          <header className="panel-header"><div><span className="eyebrow">PRIORITY QUEUE</span><h2>High-risk intelligence</h2></div><button className="text-button" onClick={() => navigate('/intelligence?min_risk=50')}>View all <ArrowRight size={14} /></button></header>
          {data.high_risk_entities.length ? (
            <div className="priority-list">
              {data.high_risk_entities.map((entity) => (
                <button key={entity.id} onClick={() => navigate(`/intelligence?entity=${entity.id}`)}>
                  <span className="entity-icon"><EntityIcon type={entity.type} /></span>
                  <span className="priority-main"><strong>{entity.display_name || entity.value}</strong><small>{friendlyType(entity.type)} · {entity.tags.map((tag) => `#${tag.name}`).join(' ')}</small></span>
                  <span className={`classification classification-${entity.classification}`}>{entity.classification}</span>
                  <span className="confidence"><i style={{ width: `${entity.confidence}%` }} />{entity.confidence}%</span>
                  <RiskBadge score={entity.risk_score} />
                </button>
              ))}
            </div>
          ) : <EmptyState title="No elevated risk" detail="Risk appears here only when transparent rules contribute points." />}
        </article>

        <article className="panel">
          <header className="panel-header"><div><span className="eyebrow">COVERAGE</span><h2>Entity distribution</h2></div><Sparkles size={17} /></header>
          <div className="distribution-list">
            {Object.entries(data.entities_by_type).sort((a, b) => b[1] - a[1]).slice(0, 7).map(([type, count]) => (
              <div key={type}><span>{friendlyType(type)}</span><div><i style={{ width: `${Math.max(8, (count / maxType) * 100)}%` }} /></div><strong>{count}</strong></div>
            ))}
          </div>
          <footer className="panel-footer"><RadioTower size={14} />{data.observation_total} source observations recorded</footer>
        </article>

        <article className="panel">
          <header className="panel-header"><div><span className="eyebrow">COLLECTION</span><h2>Collector health</h2></div><Activity size={17} /></header>
          <div className="collector-list">
            {data.collectors.map((collector) => (
              <div key={collector.id}><span className={`health-dot ${collector.last_error ? 'failed' : collector.enabled ? '' : 'disabled'}`} /><div><strong>{friendlyType(collector.name)}</strong><small>{collector.last_error ? collector.last_error : collector.enabled ? `${collector.rate_limit_per_minute} req/min` : 'disabled by configuration'}</small></div><StatusPill value={collector.last_error ? 'failed' : collector.enabled ? 'healthy' : 'disabled'} /></div>
            ))}
          </div>
          <button className="panel-action" onClick={() => navigate('/operations')}>Open collection operations <ArrowRight size={14} /></button>
        </article>

        <article className="panel">
          <header className="panel-header"><div><span className="eyebrow">CASEWORK</span><h2>Recent investigations</h2></div><BriefcaseBusiness size={17} /></header>
          {data.recent_investigations.length ? <div className="case-list">{data.recent_investigations.map((item) => <button key={item.id} onClick={() => navigate(`/investigations?id=${item.id}`)}><span className={`priority-line ${item.priority}`} /><div><strong>{item.title}</strong><small>Updated {formatDate(item.updated_at)}</small></div><StatusPill value={item.status} /></button>)}</div> : <EmptyState title="No investigations yet" detail="Promote connected intelligence into a defensible case." />}
        </article>

        <article className="panel">
          <header className="panel-header"><div><span className="eyebrow">LATEST SIGNALS</span><h2>Recent intelligence</h2></div><RadioTower size={17} /></header>
          <div className="activity-feed">{data.recent_entities.map((entity) => <div key={entity.id}><span className="feed-line" /><div><strong>{entity.value}</strong><small>{friendlyType(entity.type)} added · {formatDate(entity.first_seen)}</small></div></div>)}</div>
        </article>
      </section>
    </div>
  )
}
