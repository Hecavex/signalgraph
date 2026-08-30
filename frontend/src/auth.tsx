import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { api, setToken, token } from './api'
import type { User } from './types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  bootstrapRequired: boolean
  login: (email: string, password: string) => Promise<void>
  bootstrap: (email: string, displayName: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [bootstrapRequired, setBootstrapRequired] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const status = await api<{ bootstrap_required: boolean }>('/auth/status')
        setBootstrapRequired(status.bootstrap_required)
        if (token()) setUser(await api<User>('/auth/me'))
      } catch {
        setToken(null)
      } finally {
        setLoading(false)
      }
    }
    void load()
    const unauthorized = () => setUser(null)
    window.addEventListener('signalgraph:unauthorized', unauthorized)
    return () => window.removeEventListener('signalgraph:unauthorized', unauthorized)
  }, [])

  const authenticate = async (path: string, payload: Record<string, string>) => {
    const result = await api<{ access_token: string; user: User }>(path, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    setToken(result.access_token)
    setUser(result.user)
    setBootstrapRequired(false)
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      bootstrapRequired,
      login: (email, password) => authenticate('/auth/login', { email, password }),
      bootstrap: (email, display_name, password) =>
        authenticate('/auth/bootstrap', { email, display_name, password, role: 'admin' }),
      logout: () => {
        setToken(null)
        setUser(null)
      },
    }),
    [user, loading, bootstrapRequired],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used within AuthProvider')
  return value
}
