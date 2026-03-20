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
jest.mock('../Contexts/AppContext', () => ({
  __esModule: true,
  useAppContext: () => ({ darkMode: false }),
}))
jest.mock('../Layout/Page', () => ({
  APP_LOGO_ICON_DARK: 'dark-logo',
  APP_LOGO_ICON_LIGHT: 'light-logo',
}))

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
  it('renders method selector with two login options', async () => {
    renderLogin()
    await waitFor(() => expect(api.auth_session).toHaveBeenCalled())

    expect(screen.getByText(/log in with username and password/i)).toBeInTheDocument()
    expect(screen.getByText(/log in with api key/i)).toBeInTheDocument()
  })

  it('shows username and password fields when selecting basic auth', async () => {
    renderLogin()
    await waitFor(() => expect(api.auth_session).toHaveBeenCalled())

    fireEvent.click(screen.getByText(/log in with username and password/i))

    expect(screen.getByRole('textbox', { name: /username/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument()
  })

  it('shows API key field when selecting API key auth', async () => {
    renderLogin()
    await waitFor(() => expect(api.auth_session).toHaveBeenCalled())

    fireEvent.click(screen.getByText(/log in with api key/i))

    expect(screen.getByLabelText(/api key/i)).toBeInTheDocument()
  })

  it('navigates back to method selector via "More login options"', async () => {
    renderLogin()
    await waitFor(() => expect(api.auth_session).toHaveBeenCalled())

    fireEvent.click(screen.getByText(/log in with username and password/i))
    expect(screen.getByRole('textbox', { name: /username/i })).toBeInTheDocument()

    fireEvent.click(screen.getByText('More login options'))
    expect(screen.getByText(/log in with username and password/i)).toBeInTheDocument()
    expect(screen.getByText(/log in with api key/i)).toBeInTheDocument()
  })

  it('disables submit when fields are empty', async () => {
    renderLogin()
    await waitFor(() => expect(api.auth_session).toHaveBeenCalled())

    fireEvent.click(screen.getByText(/log in with username and password/i))

    const submitBtn = screen.getByRole('button', { name: /log in/i })
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

    fireEvent.click(screen.getByText(/log in with username and password/i))

    await userEvent.type(screen.getByRole('textbox', { name: /username/i }), 'user')
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'wrong')
    fireEvent.click(screen.getByRole('button', { name: /log in/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })
})
