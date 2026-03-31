/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

/**
 * Registry for 401 handler. AuthContext registers logout+redirect.
 * Client's Axios interceptor invokes it to avoid circular imports.
 */
let _on401 = null

export const register401Handler = (fn) => {
  _on401 = fn
}

export const get401Handler = () => _on401
