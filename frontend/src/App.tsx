import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { useAuth } from './auth'
import { Loading } from './components/Common'
import Shell from './components/Shell'
import LoginPage from './pages/LoginPage'

const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const IntelligencePage = lazy(() => import('./pages/IntelligencePage'))
const GraphPage = lazy(() => import('./pages/GraphPage'))
const InvestigationsPage = lazy(() => import('./pages/InvestigationsPage'))
const ReportsPage = lazy(() => import('./pages/ReportsPage'))
const OperationsPage = lazy(() => import('./pages/OperationsPage'))

export default function App() {
  const auth = useAuth()
  if (auth.loading) return <div className="app-loading"><Loading label="Opening SignalGraph" /></div>
  if (!auth.user) return <LoginPage />
  return <Shell><Suspense fallback={<Loading />}><Routes><Route path="/" element={<DashboardPage />} /><Route path="/intelligence" element={<IntelligencePage />} /><Route path="/graph" element={<GraphPage />} /><Route path="/investigations" element={<InvestigationsPage />} /><Route path="/reports" element={<ReportsPage />} /><Route path="/operations" element={<OperationsPage />} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></Suspense></Shell>
}
