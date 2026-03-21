/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import api from '../api'
import { getHistory } from '../history'
import { register401Handler } from '../auth401handler'
import { clearAuthReady, notifyAuthReady } from '../authEvents'

export const AuthContext = createContext()

export const useAuthContext = () => useContext(AuthContext)

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [hasCheckedSession, setHasCheckedSession] = useState(false)

  const isAuthenticated = !!user

  const logout = useCallback(() => {
    setUser(null)
    clearAuthReady()
    api.auth_logout().catch(() => {})
    const h = getHistory()
    const currentPath = h.location.pathname + h.location.search
    h.replace(`/login?next=${encodeURIComponent(currentPath)}`)
  }, [])

  const login = useCallback(async (credentials) => {
    const response = await api.auth_login(credentials)
    const u = response?.data?.user
    if (u) {
      setUser(u)
      notifyAuthReady()
    } else {
      throw new Error('Login did not return user')
    }
  }, [])

  const checkSession = useCallback(async () => {
    try {
      const response = await api.auth_session()
      const u = response?.data?.user
      setUser(u || null)
      if (u) {
        notifyAuthReady()
      } else {
        clearAuthReady()
      }
    } catch (err) {
      setUser(null)
      clearAuthReady()
    } finally {
      setHasCheckedSession(true)
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    checkSession()
  }, [checkSession])

  useEffect(() => {
    register401Handler(logout)
    return () => register401Handler(null)
  }, [logout])

  const value = {
    user,
    isAuthenticated,
    isLoading,
    hasCheckedSession,
    login,
    logout,
    checkSession,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}
