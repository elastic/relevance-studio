/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

describe('client axios interceptor', () => {
  const loadClient = ({ handler = null, appContext = null } = {}) => {
    jest.resetModules()

    const axiosMock = {
      interceptors: {
        response: {
          use: jest.fn((onSuccess, onError) => {
            axiosMock.onError = onError
            return 1
          }),
        },
      },
      request: jest.fn(),
      isCancel: jest.fn(),
    }
    const replace = jest.fn()

    jest.doMock('axios', () => axiosMock)
    jest.doMock('../auth401handler', () => ({
      get401Handler: () => handler,
    }))
    jest.doMock('../history', () => ({
      getHistory: () => ({ replace }),
    }))
    jest.doMock('../Contexts/AppContext', () => ({
      getAppContext: () => appContext,
    }))

    // Import registers the interceptor.
    // eslint-disable-next-line global-require
    require('../client').default
    return { axiosMock, replace }
  }

  it('calls registered 401 handler for protected API paths', async () => {
    const on401 = jest.fn()
    const { axiosMock, replace } = loadClient({ handler: on401 })
    const error = { response: { status: 401 }, config: { url: '/api/workspaces' } }

    await axiosMock.onError(error).catch(() => {})

    expect(on401).toHaveBeenCalledTimes(1)
    expect(replace).not.toHaveBeenCalled()
  })

  it('does not call 401 handler for auth endpoints', async () => {
    const on401 = jest.fn()
    const { axiosMock, replace } = loadClient({ handler: on401 })
    const error = { response: { status: 401 }, config: { url: '/api/auth/session' } }

    await axiosMock.onError(error).catch(() => {})

    expect(on401).not.toHaveBeenCalled()
    expect(replace).not.toHaveBeenCalled()
  })

  it('redirects to /login when no 401 handler is registered', async () => {
    const { axiosMock, replace } = loadClient()
    const error = { response: { status: 401 }, config: { url: '/api/workspaces' } }

    await axiosMock.onError(error).catch(() => {})

    expect(replace).toHaveBeenCalledWith('/login')
  })

  it('shows network error toast when request has no response', async () => {
    const addToast = jest.fn()
    const { axiosMock } = loadClient({ appContext: { addToast } })
    const error = { message: 'ECONNREFUSED', config: { url: '/api/workspaces' } }

    await axiosMock.onError(error).catch(() => {})

    expect(addToast).toHaveBeenCalledTimes(1)
    expect(addToast.mock.calls[0][0].title).toBe('Network error')
  })
})
