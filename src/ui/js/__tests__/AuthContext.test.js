/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { render, screen, waitFor } from '@testing-library/react'
import { AuthProvider, useAuthContext } from '../Contexts/AuthContext'
import api from '../api'
import { clearAuthReady, notifyAuthReady } from '../authEvents'

jest.mock('../api')
jest.mock('../authEvents', () => ({
  notifyAuthReady: jest.fn(),
  clearAuthReady: jest.fn(),
}))
jest.mock('../history', () => {
  const mockHistory = { replace: jest.fn(), location: { state: null } }
  return {
    __esModule: true,
    default: mockHistory,
    getHistory: () => mockHistory,
  }
})

const TestConsumer = () => {
  const { isAuthenticated, hasCheckedSession } = useAuthContext()
  return (
    <div>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="checked">{String(hasCheckedSession)}</span>
    </div>
  )
}

describe('AuthProvider', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('calls /api/auth/session on mount', async () => {
    api.auth_session = jest.fn().mockResolvedValue({ data: { user: { username: 'test' } } })

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    )

    await waitFor(() => expect(api.auth_session).toHaveBeenCalledWith())
    expect(api.auth_session).toHaveBeenCalledTimes(1)
  })

  it('sets isAuthenticated=true when session is valid', async () => {
    api.auth_session = jest.fn().mockResolvedValue({ data: { user: { username: 'test' } } })

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('checked')).toHaveTextContent('true')
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    })
    expect(notifyAuthReady).toHaveBeenCalledTimes(1)
    expect(clearAuthReady).not.toHaveBeenCalled()
  })

  it('sets isAuthenticated=false when session returns 401', async () => {
    api.auth_session = jest.fn().mockRejectedValue({ response: { status: 401 } })

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('checked')).toHaveTextContent('true')
      expect(screen.getByTestId('authenticated')).toHaveTextContent('false')
    })
    expect(clearAuthReady).toHaveBeenCalledTimes(1)
    expect(notifyAuthReady).not.toHaveBeenCalled()
  })
})
