/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  clearAuthReady,
  notifyAuthReady,
  registerAuthReadyHandler,
} from '../authEvents'

describe('authEvents', () => {
  beforeEach(() => {
    clearAuthReady()
  })

  it('invokes registered handler when auth-ready is notified', () => {
    const fn = jest.fn()
    registerAuthReadyHandler(fn)

    notifyAuthReady()

    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('unsubscribe removes a previously registered handler', () => {
    const fn = jest.fn()
    const unsubscribe = registerAuthReadyHandler(fn)
    unsubscribe()

    notifyAuthReady()

    expect(fn).not.toHaveBeenCalled()
  })

  it('immediately invokes handler when already ready (default behavior)', () => {
    const fn = jest.fn()
    notifyAuthReady()

    registerAuthReadyHandler(fn)

    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('does not immediately invoke when invokeIfReady=false', () => {
    const fn = jest.fn()
    notifyAuthReady()

    registerAuthReadyHandler(fn, { invokeIfReady: false })

    expect(fn).not.toHaveBeenCalled()
  })

  it('clearAuthReady resets ready state for future handlers', () => {
    notifyAuthReady()
    clearAuthReady()
    const fn = jest.fn()

    registerAuthReadyHandler(fn)

    expect(fn).not.toHaveBeenCalled()
  })
})
