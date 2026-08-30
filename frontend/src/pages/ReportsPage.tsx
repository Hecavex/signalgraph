import { Download, FilePlus2, FileText, Link2, X } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'

import { api, download } from '../api'
import { EmptyState, ErrorBanner, Loading, formatDate } from '../components/Common'
import type { Entity, PaginatedEntities, Report } from '../types'

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[] | null>(null)
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [assessment, setAssessment] = useState('')
  const [confidence, setConfidence] = useState(50)
  const [entities, setEntities] = useState<Entity[]>([])
  const [entityIds, setEntityIds] = useState<string[]>([])
  const [error, setError] = useState('')

  const load = () => api<Report[]>('/reports').then(setReports).catch((caught) => setError(caught.message))
  useEffect(() => { void load() }, [])
  useEffect(() => {
    api<PaginatedEntities>('/entities?page_size=100').then((result) => setEntities(result.items)).catch(() => undefined)
  }, [])
  const create = async (event: FormEvent) => {
    event.preventDefault()
    await api('/reports', { method: 'POST', body: JSON.stringify({ title, executive_summary: summary, assessment, confidence, entity_ids: entityIds }) })
    setOpen(false); setTitle(''); setSummary(''); setAssessment(''); setEntityIds([]); load()
  }

  const toggleEntity = (id: string) => setEntityIds((current) =>
    current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
  )

  return <div className="page-stack"><section className="page-heading compact"><div><span className="eyebrow">EXPLAINABLE OUTPUT</span><h1>Analyst reports</h1><p>Turn linked intelligence into clear assessments with explicit confidence.</p></div><button className="primary-button" onClick={() => setOpen(true)}><FilePlus2 size={16} />Create report</button></section>{error && <ErrorBanner message={error} />}{!reports ? <Loading /> : reports.length ? <section className="report-grid">{reports.map((report) => <article className="panel report-card" key={report.id}><header><span className="report-icon"><FileText size={20} /></span><span className="status-pill">{report.status}</span></header><span className="eyebrow">REPORT / {report.id.slice(0, 8)}</span><h2>{report.title}</h2><p>{report.executive_summary || 'No executive summary yet.'}</p><div className="report-meta"><span><strong>{report.confidence}%</strong>confidence</span><span><strong>{report.entities.length}</strong>linked entities</span><span><strong>{formatDate(report.updated_at)}</strong>updated</span></div><footer><span><Link2 size={14} />{report.entities.map((item) => item.value).slice(0, 2).join(', ') || 'No linked intelligence'}</span><button className="secondary-button" onClick={() => download(`/reports/${report.id}/markdown`, `${report.title}.md`)}><Download size={14} />Markdown</button></footer></article>)}</section> : <EmptyState title="No reports yet" detail="Create an assessment when your evidence is ready to communicate." />}{open && <div className="modal-backdrop" onMouseDown={() => setOpen(false)}><form className="modal-card wide-modal" onSubmit={create} onMouseDown={(event) => event.stopPropagation()}><header><div><span className="eyebrow">NEW ANALYTICAL PRODUCT</span><h2>Create report</h2></div><button className="icon-button" type="button" onClick={() => setOpen(false)}><X size={17} /></button></header><label>Report title<input required value={title} onChange={(event) => setTitle(event.target.value)} /></label><label>Executive summary<textarea required value={summary} onChange={(event) => setSummary(event.target.value)} /></label><label>Assessment<textarea className="large-textarea" value={assessment} onChange={(event) => setAssessment(event.target.value)} /></label><label>Confidence <strong>{confidence}%</strong><input type="range" min="0" max="100" value={confidence} onChange={(event) => setConfidence(Number(event.target.value))} /></label><fieldset className="entity-checklist"><legend>Linked intelligence <span>{entityIds.length} selected</span></legend>{entities.map((entity) => <label key={entity.id} className={entityIds.includes(entity.id) ? 'selected' : ''}><input type="checkbox" checked={entityIds.includes(entity.id)} onChange={() => toggleEntity(entity.id)} /><span><strong>{entity.display_name || entity.value}</strong><small>{entity.type.replaceAll('_', ' ')} · risk {entity.risk_score}</small></span></label>)}</fieldset><div className="modal-actions"><button className="primary-button">Create report</button></div></form></div>}</div>
}
