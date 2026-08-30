const API_ROOT = '/api/v1'

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : 'The request could not be completed')
    this.status = status
    this.detail = detail
  }
}

export function token(): string | null {
  return sessionStorage.getItem('signalgraph-token')
}

export function setToken(value: string | null): void {
  if (value) sessionStorage.setItem('signalgraph-token', value)
  else sessionStorage.removeItem('signalgraph-token')
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const authToken = token()
  if (authToken) headers.set('Authorization', `Bearer ${authToken}`)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_ROOT}${path}`, { ...options, headers })
  if (response.status === 401 && authToken) {
    setToken(null)
    window.dispatchEvent(new Event('signalgraph:unauthorized'))
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(response.status, body.detail ?? body)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function download(path: string, filename: string): Promise<void> {
  const response = await fetch(`${API_ROOT}${path}`, {
    headers: token() ? { Authorization: `Bearer ${token()}` } : {},
  })
  if (!response.ok) throw new ApiError(response.status, 'Export failed')
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function qs(values: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value))
  })
  const query = params.toString()
  return query ? `?${query}` : ''
}
