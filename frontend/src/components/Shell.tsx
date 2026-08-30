import {
  Activity,
  BookOpenText,
  BriefcaseBusiness,
  FileText,
  Gauge,
  LogOut,
  Network,
  Search,
  Settings,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth'
import { LogoMark } from './Common'

const navigation = [
  { to: '/', label: 'Overview', icon: Gauge },
  { to: '/intelligence', label: 'Intelligence', icon: Search },
  { to: '/graph', label: 'Graph explorer', icon: Network },
  { to: '/investigations', label: 'Investigations', icon: BriefcaseBusiness },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/operations', label: 'Operations', icon: Activity },
]

const pageNames: Record<string, string> = {
  '/': 'Intelligence overview',
  '/intelligence': 'Intelligence library',
  '/graph': 'Relationship graph',
  '/investigations': 'Investigations',
  '/reports': 'Analyst reports',
  '/operations': 'Collection operations',
}

export default function Shell({ children }: { children: ReactNode }) {
  const auth = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <LogoMark />
          <div><strong>SignalGraph</strong><span>CTI workspace</span></div>
        </div>
        <div className="workspace-label">ANALYST WORKSPACE</div>
        <nav>
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'}>
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <button onClick={() => window.open('/api/docs', '_blank', 'noopener,noreferrer')}><BookOpenText size={17} /><span>API reference</span></button>
          <button onClick={() => navigate('/operations')}><Settings size={17} /><span>Collector settings</span></button>
          <div className="analyst-card">
            <span className="avatar">{auth.user?.display_name.slice(0, 2).toUpperCase()}</span>
            <div><strong>{auth.user?.display_name}</strong><small>{auth.user?.role}</small></div>
            <button title="Sign out" onClick={auth.logout}><LogOut size={15} /></button>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">SIGNALGRAPH / V1</span>
            <strong>{pageNames[location.pathname] || 'Workspace'}</strong>
          </div>
          <form
            className="global-search"
            onSubmit={(event) => {
              event.preventDefault()
              navigate(`/intelligence?q=${encodeURIComponent(query)}`)
            }}
          >
            <Search size={16} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search any observable…" />
            <kbd>⌘ K</kbd>
          </form>
          <div className="topbar-actions">
            <span className="system-state"><i /> systems nominal</span>
            <span className="avatar-button">{auth.user?.display_name.slice(0, 2).toUpperCase()}</span>
          </div>
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  )
}
