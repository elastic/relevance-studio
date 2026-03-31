/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

/**
 * Simple in-memory auth lifecycle event bridge.
 * AuthContext emits auth-ready after successful login/session checks.
 * AppContext subscribes to re-run setup checks once auth is available.
 */
let _authReady = false
const _authReadyHandlers = new Set()

export const registerAuthReadyHandler = (fn, opts = {}) => {
  const { invokeIfReady = true } = opts
  if (typeof fn !== 'function') {
    return () => {}
  }
  _authReadyHandlers.add(fn)
  if (invokeIfReady && _authReady) {
    fn()
  }
  return () => {
    _authReadyHandlers.delete(fn)
  }
}

export const notifyAuthReady = () => {
  _authReady = true
  for (const fn of _authReadyHandlers) {
    fn()
  }
}

export const clearAuthReady = () => {
  _authReady = false
}
