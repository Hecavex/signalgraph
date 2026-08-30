import { Activity, AlertTriangle, CheckCircle2, Clock3, RefreshCcw } from 'lucide-react'
import { useEffect, useState } from 'react'

import { api } from '../api'
import { useAuth } from '../auth'
import { ErrorBanner, Loading, StatusPill, formatDate, friendlyType } from '../components/Common'
import type { Collector, Job } from '../types'

export default function OperationsPage() {
  const auth = useAuth()
  const [collectors, setCollectors] = useState<Collector[] | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [error, setError] = useState('')
  const load = () => Promise.all([api<Collector[]>('/operations/collectors'), api<Job[]>('/operations/jobs')]).then(([collectorData, jobData]) => { setCollectors(collectorData); setJobs(jobData) }).catch((caught) => setError(caught.message))
  useEffect(() => { void load() }, [])
  const retry = async (id: string) => { await api(`/operations/jobs/${id}/retry`, { method: 'POST' }); load() }
  const configure = async (name: string, changes: Partial<Collector>) => {
    try {
      await api(`/operations/collectors/${name}`, { method: 'PATCH', body: JSON.stringify(changes) })
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Collector configuration could not be saved')
    }
  }
  const isAdmin = auth.user?.role === 'admin'
  return <div className="page-stack"><section className="page-heading compact"><div><span className="eyebrow">COLLECTION CONTROL</span><h1>Collection operations</h1><p>Inspect passive collectors, rate limits, failures, and queued enrichment work.</p></div><button className="secondary-button" onClick={load}><RefreshCcw size={15} />Refresh</button></section>{error && <ErrorBanner message={error} />}{!collectors ? <Loading /> : <><section className="collector-grid">{collectors.map((collector) => <article className="panel collector-card" key={collector.id}><header><span className={`collector-symbol ${collector.last_error ? 'bad' : collector.enabled ? '' : 'off'}`}>{collector.last_error ? <AlertTriangle size={18} /> : collector.enabled ? <CheckCircle2 size={18} /> : <Activity size={18} />}</span><StatusPill value={collector.last_error ? 'failed' : collector.enabled ? 'enabled' : 'disabled'} /></header><h2>{friendlyType(collector.name)}</h2><p>{collector.last_error || 'Passive intelligence collection ready.'}</p><dl><div><dt>Rate limit</dt><dd><input aria-label={`${friendlyType(collector.name)} rate limit`} type="number" min="1" max="600" defaultValue={collector.rate_limit_per_minute} disabled={!isAdmin} onBlur={(event) => { const value = Number(event.target.value); if (value !== collector.rate_limit_per_minute) void configure(collector.name, { rate_limit_per_minute: value }) }} />/min</dd></div><div><dt>Timeout</dt><dd>{collector.timeout_seconds}s</dd></div><div><dt>Retries</dt><dd>{collector.max_retries}</dd></div><div><dt>Last success</dt><dd>{formatDate(collector.last_success_at)}</dd></div></dl><footer><button className="secondary-button" disabled={!isAdmin} onClick={() => void configure(collector.name, { enabled: !collector.enabled })}>{collector.enabled ? 'Disable collector' : 'Enable collector'}</button></footer></article>)}</section><section className="panel table-panel"><header className="panel-header padded"><div><span className="eyebrow">JOB HISTORY</span><h2>Enrichment jobs</h2></div><span>{jobs.length} retained</span></header><div className="data-table-wrap"><table className="data-table"><thead><tr><th>Observable</th><th>Collectors</th><th>Status</th><th>Attempts</th><th>Created</th><th /></tr></thead><tbody>{jobs.map((job) => <tr key={job.id}><td><strong>{job.observable}</strong>{job.error && <small className="job-error">{job.error}</small>}</td><td className="muted">{job.collector.replace('concurrent:', '').replaceAll(',', ', ')}</td><td><StatusPill value={job.status} /></td><td>{job.attempts}</td><td className="muted"><Clock3 size={13} /> {formatDate(job.created_at)}</td><td>{['failed', 'partial'].includes(job.status) && <button className="text-button" onClick={() => retry(job.id)}><RefreshCcw size={13} />Retry</button>}</td></tr>)}</tbody></table></div></section></>}</div>
}
