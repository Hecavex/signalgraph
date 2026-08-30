import { BriefcaseBusiness, Download, FileJson2, Filter, Plus, RefreshCw, Search, ShieldCheck, X } from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'

import { ApiError, api, download, qs } from '../api'
import { EmptyState, EntityIcon, EntityTable, ErrorBanner, Loading, RiskBadge, formatDate, friendlyType } from '../components/Common'
import type { Entity, Investigation, PaginatedEntities } from '../types'

export default function IntelligencePage() {
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState<PaginatedEntities | null>(null)
  const [selected, setSelected] = useState<Entity | null>(null)
  const [query, setQuery] = useState(params.get('q') || '')
  const [type, setType] = useState('')
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(params.get('new') === '1')
  const [observable, setObservable] = useState('')
  const [classification, setClassification] = useState('unknown')
  const [working, setWorking] = useState(false)
  const [investigations, setInvestigations] = useState<Investigation[]>([])
  const [investigationId, setInvestigationId] = useState('')
  const [caseNotice, setCaseNotice] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const result = await api<PaginatedEntities>(`/entities${qs({ q: params.get('q') || undefined, type: params.get('type') || undefined, min_risk: params.get('min_risk') || undefined, page: params.get('page') || 1, page_size: 25 })}`)
      setData(result)
      const selectedId = params.get('entity')
      if (selectedId) setSelected(await api<Entity>(`/entities/${selectedId}`))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to load intelligence')
    }
  }, [params])

  useEffect(() => { void load() }, [load])
  useEffect(() => {
    api<Investigation[]>('/investigations').then((items) => {
      setInvestigations(items)
      if (items[0]) setInvestigationId(items[0].id)
    }).catch(() => undefined)
  }, [])

  const search = (event: FormEvent) => {
    event.preventDefault()
    const next = new URLSearchParams(params)
    query ? next.set('q', query) : next.delete('q')
    type ? next.set('type', type) : next.delete('type')
    next.delete('page')
    setParams(next)
  }

  const create = async (event: FormEvent, enrich: boolean) => {
    event.preventDefault()
    setWorking(true)
    setError('')
    try {
      if (enrich) {
        await api('/entities/enrich', { method: 'POST', body: JSON.stringify({ value: observable }) })
      } else {
        await api('/entities', { method: 'POST', body: JSON.stringify({ value: observable, classification }) })
      }
      setObservable('')
      setFormOpen(false)
      await load()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Observable could not be saved')
    } finally {
      setWorking(false)
    }
  }

  const choose = async (entity: Entity) => {
    setSelected(await api<Entity>(`/entities/${entity.id}`))
    setCaseNotice('')
    const next = new URLSearchParams(params)
    next.set('entity', entity.id)
    setParams(next, { replace: true })
  }

  const addToInvestigation = async () => {
    if (!selected || !investigationId) return
    setWorking(true)
    setCaseNotice('')
    try {
      await api(`/investigations/${investigationId}/entities/${selected.id}`, { method: 'POST' })
      setCaseNotice('Added to investigation')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to add intelligence to the case')
    } finally {
      setWorking(false)
    }
  }

  return (
    <div className="page-stack">
      <section className="page-heading compact">
        <div><span className="eyebrow">NORMALIZED KNOWLEDGE</span><h1>Intelligence library</h1><p>Search observables, inspect provenance, and move through connected infrastructure.</p></div>
        <div className="heading-actions"><button className="secondary-button" onClick={() => download('/exchange/csv', 'signalgraph-iocs.csv')}><Download size={15} />IOC CSV</button><button className="secondary-button" onClick={() => download('/exchange/stix', 'signalgraph-stix.json')}><FileJson2 size={15} />STIX 2.1</button><button className="primary-button" onClick={() => setFormOpen(true)}><Plus size={16} />Add observable</button></div>
      </section>
      {error && <ErrorBanner message={error} />}
      <form className="filter-bar" onSubmit={search}>
        <div className="search-input"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Domain, IP, URL, hash, CVE…" /></div>
        <div className="select-input"><Filter size={15} /><select value={type} onChange={(event) => setType(event.target.value)}><option value="">All entity types</option><option value="domain">Domains</option><option value="ip_address">IP addresses</option><option value="url">URLs</option><option value="file_hash">File hashes</option><option value="certificate">Certificates</option><option value="vulnerability">Vulnerabilities</option></select></div>
        <button className="secondary-button" type="submit">Apply filters</button>
        <span className="result-count">{data?.total ?? '—'} entities</span>
      </form>
      {!data ? <Loading /> : data.items.length ? <section className="panel table-panel"><EntityTable entities={data.items} onSelect={choose} /><footer className="pagination"><button disabled={data.page <= 1} onClick={() => { const next = new URLSearchParams(params); next.set('page', String(data.page - 1)); setParams(next) }}>Previous</button><span>Page {data.page} of {data.pages}</span><button disabled={data.page >= data.pages} onClick={() => { const next = new URLSearchParams(params); next.set('page', String(data.page + 1)); setParams(next) }}>Next</button></footer></section> : <EmptyState title="No matching intelligence" detail="Add an observable or broaden your search filters." />}

      {formOpen && <div className="modal-backdrop" onMouseDown={() => setFormOpen(false)}><form className="modal-card" onSubmit={(event) => create(event, false)} onMouseDown={(event) => event.stopPropagation()}><header><div><span className="eyebrow">NEW SIGNAL</span><h2>Add an observable</h2></div><button type="button" className="icon-button" onClick={() => setFormOpen(false)}><X size={17} /></button></header><p>SignalGraph identifies supported observable types and stores a normalized, deduplicated value.</p><label>Observable<input autoFocus required value={observable} onChange={(event) => setObservable(event.target.value)} placeholder="example.org, 203.0.113.10, CVE-2025-…" /></label><label>Initial classification<select value={classification} onChange={(event) => setClassification(event.target.value)}><option value="unknown">Unknown</option><option value="benign">Benign</option><option value="suspicious">Suspicious</option><option value="malicious">Malicious</option></select></label><div className="modal-actions"><button type="button" className="secondary-button" disabled={working || !observable} onClick={(event) => void create(event as unknown as FormEvent, true)}><RefreshCw size={15} />Add & enrich</button><button className="primary-button" disabled={working}>{working ? 'Saving…' : 'Add to library'}</button></div><small className="safety-note"><ShieldCheck size={14} />Enrichment is passive-first and never fetches the submitted target directly.</small></form></div>}

      {selected && <aside className="detail-drawer"><header><div className="entity-heading"><span className="entity-icon large"><EntityIcon type={selected.type} size={21} /></span><div><span className="eyebrow">{friendlyType(selected.type)}</span><h2>{selected.display_name || selected.value}</h2></div></div><button className="icon-button" onClick={() => { setSelected(null); const next = new URLSearchParams(params); next.delete('entity'); setParams(next, { replace: true }) }}><X size={17} /></button></header><div className="drawer-score"><RiskBadge score={selected.risk_score} /><div><strong>Transparent risk score</strong><span>{selected.classification} · {selected.confidence}% confidence</span></div></div><section><span className="eyebrow">NORMALIZED VALUE</span><code>{selected.normalized_value}</code><div className="tag-row">{selected.tags.map((tag) => <span key={tag.id}>#{tag.name}</span>)}</div></section><section><div className="section-title"><h3>Why this score</h3><span>{selected.risk_explanation.length} rules</span></div>{selected.risk_explanation.length ? <div className="reason-list">{selected.risk_explanation.map((reason) => <div key={reason.rule}><b>+{reason.points}</b><span><strong>{reason.rule.replaceAll('_', ' ')}</strong><small>{reason.reason}</small></span></div>)}</div> : <p className="muted">No risk rules currently contribute points.</p>}</section><section><div className="section-title"><h3>Source observations</h3><span>{selected.observations?.length || 0}</span></div>{selected.observations?.length ? <div className="observation-list">{selected.observations.map((observation) => <div key={observation.id}><span className="source-monogram">{observation.source.name.slice(0, 2).toUpperCase()}</span><div><strong>{observation.source.name}</strong><small>{formatDate(observation.observed_at)} · confidence {observation.confidence}%</small></div></div>)}</div> : <p className="muted">No collector observations yet.</p>}</section><section className="case-linker"><div className="section-title"><h3>Add to investigation</h3><BriefcaseBusiness size={15} /></div>{investigations.length ? <><select aria-label="Investigation" value={investigationId} onChange={(event) => setInvestigationId(event.target.value)}>{investigations.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select><button className="secondary-button" disabled={working || !investigationId} onClick={() => void addToInvestigation()}><Plus size={14} />Add evidence</button>{caseNotice && <small className="success-note">{caseNotice}</small>}</> : <p className="muted">Create an investigation before attaching evidence.</p>}</section><footer><button className="secondary-button" onClick={() => { setObservable(selected.value); setFormOpen(true) }}><RefreshCw size={15} />Enrich again</button><button className="primary-button" onClick={() => window.location.assign(`/graph?entity=${selected.id}`)}>Explore graph</button></footer></aside>}
    </div>
  )
}
