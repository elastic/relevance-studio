/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EuiProvider } from '@elastic/eui'
import { AuthProvider } from '../Contexts/AuthContext'
import Login from '../components/Login'
import api from '../api'
import history from '../history'

jest.mock('../api')
jest.mock('../history', () => {
  const mockHistory = { replace: jest.fn(), location: { state: null } }
  return {
    __esModule: true,
    default: mockHistory,
    getHistory: () => mockHistory,
  }
})

const renderLogin = () => {
  return render(
    <EuiProvider>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </EuiProvider>
  )
}

beforeEach(() => {
  jest.clearAllMocks()
  api.auth_session = jest.fn().mockRejectedValue({ response: { status: 401 } })
  api.auth_login = jest.fn().mockResolvedValue({ data: { user: { username: 'test' } } })
})

describe('Login', () => {
  it('renders username and password fields in basic auth mode', async () => {
    renderLogin()
    await waitFor(() => expect(api.auth_session).toHaveBeenCalled())

    expect(screen.getByRole('textbox', { name: /username/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('renders API key field in API key mode', async () => {
    renderLogin()
    await waitFor(() => expect(api.auth_session).toHaveBeenCalled())

    const switchEl = screen.getByRole('switch', { name: /username & password/i })
    fireEvent.click(switchEl)

    expect(screen.getByPlaceholderText(/base64-encoded api key/i)).toBeInTheDocument()
  })

  it('toggles between modes', async () => {
    renderLogin()
    await waitFor(() => expect(api.auth_session).toHaveBeenCalled())

    expect(screen.getByRole('textbox', { name: /username/i })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('switch', { name: /username & password/i }))
    expect(screen.queryByRole('textbox', { name: /username/i })).not.toBeInTheDocument()
    expect(screen.getByPlaceholderText(/base64-encoded api key/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('switch', { name: /api key/i }))
    expect(screen.getByRole('textbox', { name: /username/i })).toBeInTheDocument()
  })

  it('disables submit when fields are empty', async () => {
    renderLogin()
    await waitFor(() => expect(api.auth_session).toHaveBeenCalled())

    const submitBtn = screen.getByRole('button', { name: /sign in/i })
    expect(submitBtn).toBeDisabled()

    await userEvent.type(screen.getByRole('textbox', { name: /username/i }), 'user')
    expect(submitBtn).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/^Password$/i), 'pass')
    expect(submitBtn).not.toBeDisabled()
  })

  it('shows error message when login fails', async () => {
    api.auth_login = jest.fn().mockRejectedValue({ response: { data: { message: 'Invalid credentials' } } })

    renderLogin()
    await waitFor(() => expect(api.auth_session).toHaveBeenCalled())

    await userEvent.type(screen.getByRole('textbox', { name: /username/i }), 'user')
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'wrong')
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })
})
