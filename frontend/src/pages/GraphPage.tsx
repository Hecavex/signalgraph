import cytoscape, { type Core, type NodeSingular } from 'cytoscape'
import { Focus, Layers3, Network, SlidersHorizontal } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { api } from '../api'
import { EmptyState, ErrorBanner, Loading, RiskBadge, friendlyType } from '../components/Common'
import type { Entity, GraphData, PaginatedEntities } from '../types'

const colors: Record<string, string> = {
  domain: '#62d6c6', hostname: '#62d6c6', ip_address: '#79aef7', certificate: '#b69cf7',
  asn: '#f5bd68', organization: '#d9e2e8', vulnerability: '#ef7c79', file_hash: '#ee8fc4', malware: '#ef7c79',
}

const entityFilterOptions = [
  'domain', 'hostname', 'ip_address', 'certificate', 'asn', 'organization',
  'vulnerability', 'file_hash', 'malware',
]
const relationshipFilterOptions = [
  'resolves_to', 'dns_cname', 'dns_mx', 'dns_ns', 'registered_by',
  'observed_in_certificate', 'shares_certificate', 'seen_in_urlscan',
  'announced_by', 'operated_by', 'sample_of',
]

export default function GraphPage() {
  const container = useRef<HTMLDivElement>(null)
  const graphRef = useRef<Core | null>(null)
  const [params, setParams] = useSearchParams()
  const [entities, setEntities] = useState<Entity[]>([])
  const [graph, setGraph] = useState<GraphData | null>(null)
  const [selected, setSelected] = useState<GraphData['nodes'][number] | null>(null)
  const [depth, setDepth] = useState(Number(params.get('depth') || 2))
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [entityFilters, setEntityFilters] = useState<string[]>([])
  const [relationshipFilters, setRelationshipFilters] = useState<string[]>([])
  const [error, setError] = useState('')
  const investigationId = params.get('investigation')

  useEffect(() => {
    api<PaginatedEntities>('/entities?page_size=100').then((result) => {
      setEntities(result.items)
      if (!params.get('entity') && !params.get('investigation') && result.items[0]) {
        const next = new URLSearchParams(params)
        next.set('entity', result.items[0].id)
        setParams(next, { replace: true })
      }
    }).catch((caught) => setError(caught.message))
  }, []) // initial selection only

  useEffect(() => {
    const entityId = params.get('entity')
    const investigation = params.get('investigation')
    if (!entityId && !investigation) return
    setGraph(null)
    const query = new URLSearchParams({ depth: String(depth) })
    entityFilters.forEach((value) => query.append('entity_type', value))
    relationshipFilters.forEach((value) => query.append('relationship_type', value))
    const endpoint = investigation
      ? `/investigations/${investigation}/graph`
      : `/graph/${entityId}?${query}`
    api<GraphData>(endpoint).then((result) => {
      if (!investigation) {
        setGraph(result)
        return
      }
      const nodes = entityFilters.length
        ? result.nodes.filter((node) => entityFilters.includes(node.type))
        : result.nodes
      const nodeIds = new Set(nodes.map((node) => node.id))
      const edges = result.edges.filter((edge) =>
        nodeIds.has(edge.source)
        && nodeIds.has(edge.target)
        && (!relationshipFilters.length || relationshipFilters.includes(edge.type)),
      )
      setGraph({ ...result, nodes, edges })
    }).catch((caught) => setError(caught.message))
  }, [params, depth, entityFilters, relationshipFilters])

  useEffect(() => {
    if (!container.current || !graph) return
    graphRef.current?.destroy()
    graphRef.current = cytoscape({
      container: container.current,
      elements: [
        ...graph.nodes.map((node) => ({ data: { ...node, label: node.label.length > 28 ? `${node.label.slice(0, 26)}…` : node.label } })),
        ...graph.edges.map((edge) => ({ data: { ...edge, label: edge.type.replaceAll('_', ' ') } })),
      ],
      style: [
        { selector: 'node', style: { 'background-color': (element: NodeSingular) => colors[element.data('type')] || '#9aa8b1', label: 'data(label)', color: '#d9e2e8', 'font-family': 'Inter, system-ui', 'font-size': 10, 'text-valign': 'bottom', 'text-margin-y': 8, width: (element: NodeSingular) => 24 + Math.min(18, element.data('risk_score') / 5), height: (element: NodeSingular) => 24 + Math.min(18, element.data('risk_score') / 5), 'border-width': 2, 'border-color': '#111b24' } },
        { selector: 'edge', style: { width: 1.3, 'line-color': '#344451', 'target-arrow-color': '#506575', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', label: 'data(label)', color: '#71818c', 'font-size': 7, 'text-background-color': '#101820', 'text-background-opacity': 0.9, 'text-background-padding': '3px' } },
        { selector: ':selected', style: { 'border-color': '#ffffff', 'border-width': 3, 'line-color': '#62d6c6' } },
      ],
      layout: {
        name: 'breadthfirst',
        animate: false,
        padding: 70,
        directed: true,
        spacingFactor: 1.65,
        avoidOverlap: true,
      },
      minZoom: 0.35,
      maxZoom: 2.5,
    })
    graphRef.current.on('tap', 'node', (event) => setSelected(graph.nodes.find((node) => node.id === event.target.id()) || null))
    return () => graphRef.current?.destroy()
  }, [graph])

  const rootId = params.get('entity') || investigationId || ''
  const toggleFilter = (
    value: string,
    current: string[],
    setter: (next: string[]) => void,
  ) => setter(current.includes(value) ? current.filter((item) => item !== value) : [...current, value])

  return (
    <div className="page-stack graph-page">
      <section className="page-heading compact"><div><span className="eyebrow">CONNECTED CONTEXT</span><h1>Relationship graph</h1><p>Expand bounded neighborhoods and keep every edge tied to observed evidence.</p></div><button className="secondary-button" onClick={() => graphRef.current?.fit(undefined, 50)}><Focus size={15} />Fit graph</button></section>
      {error && <ErrorBanner message={error} />}
      <section className="graph-toolbar panel">
        {investigationId
          ? <div className="case-graph-scope"><span>Graph scope</span><strong>Current investigation</strong></div>
          : <label>Starting entity<select value={rootId} onChange={(event) => { const next = new URLSearchParams(params); next.set('entity', event.target.value); setParams(next) }}>{entities.map((entity) => <option key={entity.id} value={entity.id}>{entity.value} · {friendlyType(entity.type)}</option>)}</select></label>}
        {!investigationId && <label>Expansion depth<div className="segmented">{[1, 2, 3].map((value) => <button key={value} className={depth === value ? 'active' : ''} onClick={() => setDepth(value)}>{value}</button>)}</div></label>}
        <span className="graph-count"><Network size={16} />{graph?.nodes.length || 0} nodes · {graph?.edges.length || 0} edges</span>
        <button className={`icon-button ${filtersOpen ? 'active' : ''}`} title="Graph filters" aria-expanded={filtersOpen} onClick={() => setFiltersOpen((value) => !value)}><SlidersHorizontal size={17} /></button>
      </section>
      {filtersOpen && <section className="graph-filter-panel panel"><div><span className="eyebrow">ENTITY TYPES</span><div className="filter-pills">{entityFilterOptions.map((value) => <label key={value} className={entityFilters.includes(value) ? 'active' : ''}><input type="checkbox" checked={entityFilters.includes(value)} onChange={() => toggleFilter(value, entityFilters, setEntityFilters)} />{friendlyType(value)}</label>)}</div></div><div><span className="eyebrow">RELATIONSHIPS</span><div className="filter-pills">{relationshipFilterOptions.map((value) => <label key={value} className={relationshipFilters.includes(value) ? 'active' : ''}><input type="checkbox" checked={relationshipFilters.includes(value)} onChange={() => toggleFilter(value, relationshipFilters, setRelationshipFilters)} />{friendlyType(value)}</label>)}</div></div><button className="text-button" disabled={!entityFilters.length && !relationshipFilters.length} onClick={() => { setEntityFilters([]); setRelationshipFilters([]) }}>Clear filters</button></section>}
      <section className="graph-workspace panel">
        {!rootId ? <EmptyState title="No graph seed" detail="Add intelligence before exploring relationships." /> : !graph ? <Loading label="Expanding neighborhood" /> : !graph.nodes.length ? <EmptyState title="No matching graph" detail="Clear filters or add linked intelligence to this investigation." /> : <>
          <div ref={container} className="graph-canvas" aria-label="Interactive relationship graph" />
          <div className="graph-legend">{Object.entries(colors).slice(0, 7).map(([type, color]) => <span key={type}><i style={{ background: color }} />{friendlyType(type)}</span>)}</div>
          <div className="graph-safety"><Layers3 size={15} />Depth is capped at 3 and results at 500 nodes.</div>
        </>}
        {selected && <aside className="graph-inspector"><span className="eyebrow">SELECTED NODE</span><h3>{selected.label}</h3><p>{friendlyType(selected.type)}</p><div><RiskBadge score={selected.risk_score} /><span>{selected.classification}</span></div><button className="primary-button" onClick={() => { const next = new URLSearchParams(params); next.delete('investigation'); next.set('entity', selected.id); setParams(next); setSelected(null) }}>Pivot from node</button></aside>}
      </section>
    </div>
  )
}
