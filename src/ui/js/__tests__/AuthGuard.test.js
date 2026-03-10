/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { render, screen, waitFor } from '@testing-library/react'
import { Router } from 'react-router-dom'
import { createMemoryHistory } from 'history'
import { AuthProvider } from '../Contexts/AuthContext'
import { AuthGuard } from '../Routes'
import api from '../api'

jest.mock('../api')

jest.mock('../history', () => {
  const { createMemoryHistory } = require('history')
  const h = createMemoryHistory()
  return {
    __esModule: true,
    default: h,
    getHistory: () => h,
  }
})

const history = require('../history').default

describe('AuthGuard', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    history.replace('/')
  })

  it('renders children when isAuthenticated=true', async () => {
    api.auth_session = jest.fn().mockResolvedValue({ data: { user: { username: 'test' } } })

    render(
      <Router history={history}>
        <AuthProvider>
          <AuthGuard>
            <div data-testid="protected-content">Protected</div>
          </AuthGuard>
        </AuthProvider>
      </Router>
    )

    await waitFor(() => {
      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      expect(screen.getByTestId('protected-content')).toHaveTextContent('Protected')
    })
  })

  it('redirects to /login when isAuthenticated=false', async () => {
    api.auth_session = jest.fn().mockRejectedValue({ response: { status: 401 } })
    history.replace('/workspaces')

    render(
      <Router history={history}>
        <AuthProvider>
          <AuthGuard>
            <div data-testid="protected-content">Protected</div>
          </AuthGuard>
        </AuthProvider>
      </Router>
    )

    await waitFor(() => expect(api.auth_session).toHaveBeenCalled())

    expect(history.location.pathname).toBe('/login')
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
  })
})
