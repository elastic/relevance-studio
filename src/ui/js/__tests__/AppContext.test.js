/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { render, screen, waitFor, act } from '@testing-library/react'
import { AppProvider, useAppContext } from '../Contexts/AppContext'
import api from '../api'

let onAuthReady = null

jest.mock('../api')
jest.mock('../authEvents', () => ({
  registerAuthReadyHandler: jest.fn((fn) => {
    onAuthReady = fn
    return jest.fn()
  }),
}))

const ContextProbe = () => {
  const {
    hasCheckedSetup,
    deploymentMode,
    isSetup,
    isCheckingSetup,
  } = useAppContext()
  return (
    <div>
      <span data-testid='checked'>{String(hasCheckedSetup)}</span>
      <span data-testid='mode'>{String(deploymentMode)}</span>
      <span data-testid='setup'>{String(isSetup)}</span>
      <span data-testid='checking'>{String(isCheckingSetup)}</span>
    </div>
  )
}

describe('AppProvider setup bootstrap', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    onAuthReady = null
  })

  it('defers setup state when initial setup_check returns 401', async () => {
    api.setup_check = jest.fn().mockRejectedValue({ response: { status: 401 } })

    render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>
    )

    await waitFor(() => {
      expect(api.setup_check).toHaveBeenCalledTimes(1)
      expect(screen.getByTestId('checked')).toHaveTextContent('false')
      expect(screen.getByTestId('mode')).toHaveTextContent('null')
      expect(screen.getByTestId('setup')).toHaveTextContent('null')
      expect(screen.getByTestId('checking')).toHaveTextContent('false')
    })
  })

  it('re-checks setup after auth-ready and updates state without reload', async () => {
    api.setup_check = jest
      .fn()
      .mockRejectedValueOnce({ response: { status: 401 } })
      .mockResolvedValueOnce({
        data: {
          deployment: { mode: 'local', license: { type: 'trial', status: 'active' } },
          setup: { failures: 0, requests: [], upgrade_only_failures: false },
          upgrade: { upgrade_needed: false, pending_steps: [], pending_versions: [] },
          version: '1.2.3',
        },
      })

    render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('checked')).toHaveTextContent('false')
    })

    await act(async () => {
      await onAuthReady()
    })

    await waitFor(() => {
      expect(api.setup_check).toHaveBeenCalledTimes(2)
      expect(screen.getByTestId('checked')).toHaveTextContent('true')
      expect(screen.getByTestId('mode')).toHaveTextContent('local')
      expect(screen.getByTestId('setup')).toHaveTextContent('true')
    })
  })
})
