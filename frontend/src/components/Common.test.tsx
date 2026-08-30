import { render, screen } from '@testing-library/react'

import { RiskBadge, friendlyType } from './Common'

describe('analyst display helpers', () => {
  it('renders explained score severity without presenting a verdict', () => {
    const { rerender } = render(<RiskBadge score={72} />)
    expect(screen.getByTitle('Risk score 72 out of 100')).toHaveClass('risk-critical')
    rerender(<RiskBadge score={12} />)
    expect(screen.getByTitle('Risk score 12 out of 100')).toHaveClass('risk-guarded')
  })

  it('formats internal entity types for humans', () => {
    expect(friendlyType('ip_address')).toBe('ip address')
    expect(friendlyType('threat_actor')).toBe('threat actor')
  })
})
