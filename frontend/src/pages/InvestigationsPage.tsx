import { BookOpen, ChevronRight, Clock3, Download, MessageSquarePlus, Network, Plus, Save, X } from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { ApiError, api, download } from '../api'
import { EmptyState, ErrorBanner, Loading, StatusPill, formatDate } from '../components/Common'
import type { Investigation } from '../types'

interface TimelineEvent { type: string; at: string; label: string; author?: string }

export default function InvestigationsPage() {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const [items, setItems] = useState<Investigation[]>([])
  const [selected, setSelected] = useState<Investigation | null>(null)
  const [timeline, setTimeline] = useState<TimelineEvent[]>([])
  const [creating, setCreating] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const result = await api<Investigation[]>('/investigations')
      setItems(result)
      const id = params.get('id') || result[0]?.id
      if (id) {
        setSelected(await api<Investigation>(`/investigations/${id}`))
        setTimeline(await api<TimelineEvent[]>(`/investigations/${id}/timeline`))
      }
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : 'Unable to load investigations') }
  }, [params])

  useEffect(() => { void load() }, [load])

  const create = async (event: FormEvent) => {
    event.preventDefault()
    const result = await api<Investigation>('/investigations', { method: 'POST', body: JSON.stringify({ title, description, priority: 'medium' }) })
    setCreating(false); setTitle(''); setDescription('')
    setParams({ id: result.id })
  }

  const update = async (changes: Partial<Investigation>) => {
    if (!selected) return
    await api(`/investigations/${selected.id}`, { method: 'PATCH', body: JSON.stringify(changes) })
    await load()
  }

  const addNote = async (event: FormEvent) => {
    event.preventDefault()
    if (!selected || !note.trim()) return
    await api(`/investigations/${selected.id}/notes`, { method: 'POST', body: JSON.stringify({ body: note }) })
    setNote(''); await load()
  }

  return (
    <div className="page-stack">
      <section className="page-heading compact"><div><span className="eyebrow">ANALYST CASEWORK</span><h1>Investigations</h1><p>Collect evidence, document reasoning, and separate observed facts from assessment.</p></div><button className="primary-button" onClick={() => setCreating(true)}><Plus size={16} />New investigation</button></section>
      {error && <ErrorBanner message={error} />}
      <section className="investigation-layout">
        <article className="panel case-index"><header><span className="eyebrow">CASE INDEX</span><strong>{items.length} investigations</strong></header>{!items.length ? <EmptyState title="No casework" detail="Create an investigation to organize evidence." /> : items.map((item) => <button key={item.id} className={selected?.id === item.id ? 'active' : ''} onClick={() => setParams({ id: item.id })}><span className={`priority-line ${item.priority}`} /><div><strong>{item.title}</strong><small>{formatDate(item.updated_at)} · {item.priority} priority</small></div><StatusPill value={item.status} /><ChevronRight size={15} /></button>)}</article>
        {!selected ? <article className="panel"><Loading label="Opening case" /></article> : <article className="panel case-detail"><header className="case-detail-header"><div><span className="eyebrow">INVESTIGATION / {selected.id.slice(0, 8)}</span><h2>{selected.title}</h2><p>{selected.description}</p><div className="case-actions"><button className="secondary-button" disabled={!selected.entities?.length} onClick={() => navigate(`/graph?investigation=${selected.id}`)}><Network size={14} />Open case graph</button><button className="secondary-button" onClick={() => download(`/investigations/${selected.id}/export`, `investigation-${selected.id}.json`)}><Download size={14} />Export JSON</button></div></div><div><select value={selected.status} onChange={(event) => void update({ status: event.target.value as Investigation['status'] })}><option value="open">Open</option><option value="investigating">Investigating</option><option value="monitoring">Monitoring</option><option value="closed">Closed</option></select><span className="confidence-large">{selected.confidence}%<small>confidence</small></span></div></header><div className="case-columns"><section><div className="section-title"><h3>Linked intelligence</h3><span>{selected.entities?.length || 0}</span></div>{selected.entities?.length ? <div className="linked-entity-list">{selected.entities.map(({ entity }) => <div key={entity.id}><span>{entity.type.slice(0, 2).toUpperCase()}</span><div><strong>{entity.value}</strong><small>{entity.type.replaceAll('_', ' ')} · risk {entity.risk_score}</small></div></div>)}</div> : <EmptyState title="No linked entities" detail="Add entities from the intelligence library." />}<div className="case-relation-summary"><Network size={14} />{selected.relationships?.length || 0} source-backed relationships included</div><div className="assessment-editor"><div className="section-title"><h3>Analyst assessment</h3><BookOpen size={15} /></div><textarea defaultValue={selected.assessment || ''} id="assessment" placeholder="State what the evidence supports, limitations, and alternative explanations…" /><button className="secondary-button" onClick={() => void update({ assessment: (document.getElementById('assessment') as HTMLTextAreaElement).value })}><Save size={14} />Save assessment</button></div></section><section><div className="section-title"><h3>Timeline</h3><Clock3 size={15} /></div><div className="timeline">{timeline.map((event, index) => <div key={`${event.at}-${index}`}><i /><div><strong>{event.type.replaceAll('_', ' ')}</strong><p>{event.label}</p><small>{event.author ? `${event.author} · ` : ''}{formatDate(event.at)}</small></div></div>)}</div><form className="note-form" onSubmit={addNote}><label><MessageSquarePlus size={15} />Add case note</label><textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Record a source, observation, or analytical decision…" /><button className="primary-button" disabled={!note.trim()}>Add to timeline</button></form></section></div></article>}
      </section>
      {creating && <div className="modal-backdrop" onMouseDown={() => setCreating(false)}><form className="modal-card" onSubmit={create} onMouseDown={(event) => event.stopPropagation()}><header><div><span className="eyebrow">NEW CASE</span><h2>Create investigation</h2></div><button className="icon-button" type="button" onClick={() => setCreating(false)}><X size={17} /></button></header><label>Title<input autoFocus required minLength={3} value={title} onChange={(event) => setTitle(event.target.value)} /></label><label>Purpose and scope<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label><div className="modal-actions"><button className="primary-button">Create investigation</button></div></form></div>}
    </div>
  )
}
