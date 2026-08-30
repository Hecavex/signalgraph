import { qs, setToken, token } from './api'

describe('API utilities', () => {
  it('keeps access tokens in session storage only', () => {
    setToken('temporary-token')
    expect(token()).toBe('temporary-token')
    expect(localStorage.getItem('signalgraph-token')).toBeNull()
    setToken(null)
    expect(token()).toBeNull()
  })

  it('encodes only defined query parameters', () => {
    expect(qs({ q: 'north star', page: 2, type: undefined })).toBe('?q=north+star&page=2')
  })
})
