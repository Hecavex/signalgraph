import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import LoginPage from './LoginPage'

const login = vi.fn().mockResolvedValue(undefined)
vi.mock('../auth', () => ({ useAuth: () => ({ bootstrapRequired: true, login }) }))

it('requires terminal ownership and never offers a web bootstrap form', async () => {
  render(<LoginPage />)
  expect(screen.getByText('Owner setup requires the terminal')).toBeInTheDocument()
  expect(screen.getByText('docker compose exec api signalgraph create-admin')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /create administrator/i })).not.toBeInTheDocument()
  expect(screen.queryByLabelText('Display name')).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'owner@example.com' } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'StrongPassword2026' } })
  fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
  await waitFor(() => expect(login).toHaveBeenCalledWith('owner@example.com', 'StrongPassword2026'))
})
