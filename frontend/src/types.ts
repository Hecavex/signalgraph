export type Role = 'admin' | 'analyst' | 'viewer'

export interface User {
  id: string
  email: string
  display_name: string
  role: Role
  is_active: boolean
  created_at: string
}

export interface Tag {
  id: string
  name: string
  color: string
}

export interface RiskReason {
  rule: string
  points: number
  reason: string
}

export interface Source {
  id: string
  name: string
  kind: string
  url?: string
  reliability: number
}

export interface Observation {
  id: string
  observed_at: string
  confidence: number
  data: Record<string, unknown>
  source: Source
  raw_response?: {
    id: string
    collector: string
    request_url: string
    status_code: number
    sha256: string
    payload: Record<string, unknown> | unknown[]
    collected_at: string
  }
}

export interface Entity {
  id: string
  type: string
  value: string
  normalized_value: string
  display_name?: string
  description?: string
  classification: 'unknown' | 'benign' | 'suspicious' | 'malicious'
  confidence: number
  risk_score: number
  risk_explanation: RiskReason[]
  first_seen: string
  last_seen: string
  tags: Tag[]
  observations?: Observation[]
}

export interface PaginatedEntities {
  items: Entity[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface Collector {
  id: string
  name: string
  enabled: boolean
  rate_limit_per_minute: number
  timeout_seconds: number
  max_retries: number
  configuration: Record<string, unknown>
  last_success_at?: string
  last_error_at?: string
  last_error?: string
}

export interface Investigation {
  id: string
  title: string
  description?: string
  status: 'open' | 'investigating' | 'monitoring' | 'closed'
  priority: string
  assessment?: string
  confidence: number
  created_at: string
  updated_at: string
  entities?: { entity: Entity; added_at: string }[]
  relationships?: {
    relationship: {
      id: string
      source_entity_id: string
      target_entity_id: string
      type: string
      confidence: number
    }
    added_at: string
  }[]
  notes?: { id: string; body: string; created_at: string; author: User }[]
}

export interface Report {
  id: string
  title: string
  executive_summary: string
  assessment: string
  confidence: number
  status: string
  created_at: string
  updated_at: string
  entities: Entity[]
}

export interface Job {
  id: string
  task_id?: string
  collector: string
  observable: string
  status: string
  attempts: number
  error?: string
  result: Record<string, unknown>
  started_at?: string
  finished_at?: string
  created_at: string
}

export interface DashboardData {
  entity_total: number
  investigation_total: number
  observation_total: number
  relationship_total: number
  high_risk_total: number
  entities_by_type: Record<string, number>
  recent_entities: Entity[]
  recent_investigations: Investigation[]
  high_risk_entities: Entity[]
  collectors: Collector[]
}

export interface GraphData {
  nodes: { id: string; label: string; type: string; risk_score: number; classification: string }[]
  edges: { id: string; source: string; target: string; type: string; confidence: number }[]
  depth: number
}
