/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License;
 * you may not use this file except in compliance with the Elastic License.
 */

import { createContext, useContext, useEffect, useState, useMemo } from 'react'
import { EuiGlobalToastList } from '@elastic/eui'
import api from '../api'

let _appContext = null
export const getAppContext = () => _appContext

export const AppContext = createContext()

export const useAppContext = () => useContext(AppContext)

export const AppProvider = ({ children }) => {

  ////  State  /////////////////////////////////////////////////////////////////

  // Local storage state
  const [autoRefresh, setAutoRefresh] = useState(() => {
    const val = localStorage.getItem('autoRefresh')
    return val === null ? true : val === 'true' // defaults to true
  })
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('darkMode') === 'true' // defaults to false
  })
  const [deploymentMode, setDeploymentMode] = useState(() => {
    const stored = localStorage.getItem('deploymentMode')
    return stored === 'serverless' || stored === 'cloud' || stored === 'standard' ? stored : null // defaults to null
  })
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const val = localStorage.getItem('sidebarOpen')
    return val === null ? false : val === 'true'; // defaults to false
  })
  useEffect(() => localStorage.setItem('autoRefresh', autoRefresh), [autoRefresh])
  useEffect(() => localStorage.setItem('darkMode', darkMode), [darkMode])
  useEffect(() => localStorage.setItem('deploymentMode', deploymentMode), [deploymentMode])
  useEffect(() => localStorage.setItem('sidebarOpen', sidebarOpen), [sidebarOpen])

  // Toasts
  const [toasts, setToasts] = useState([])
  const addToast = (toast) => {
    toast.id = `${Date.now()}-${Math.random()}`;
    setToasts(toasts.concat(toast))
  }
  const dismissToast = (removedToast) => {
    setToasts((toasts) => toasts.filter((toast) => toast.id !== removedToast.id))
  }
  useEffect(() => {
    _appContext = { addToast } // make addToast globally available
    return () => { _appContext = null }
  }, [addToast])

  // Check setup
  const [isSetup, setIsSetup] = useState(null)
  useEffect(() => {
    const checkSetup = async () => {
      try {
        const response = await api.setup_check()

        // Check deployment mode
        if (response?.data?.deployment?.mode)
          setDeploymentMode(response.data.deployment.mode)

        // Check if setup is complete
        if ((response?.data?.setup?.failures ?? 0) > 0)
          setIsSetup(false)
        else
          setIsSetup(true)
      } catch (e) {
        console.error(e)
        setIsSetup(false)
      }
    }
    checkSetup()
  }, [])

  // Get deployment mode
  useEffect(() => {
    const getDeploymentMode = async () => {
      try {
        const response = await api.mode_get()
        setDeploymentMode(response.data.mode)
      } catch (e) {
        console.error('Failed to load mode:', e)
        setDeploymentMode(null)
      }
    }
    getDeploymentMode()
  }, [])

  const value = useMemo(() => ({
    addToast,
    autoRefresh,
    darkMode,
    deploymentMode,
    isSetup,
    sidebarOpen,
    setAutoRefresh,
    setDarkMode,
    setDeploymentMode,
    setIsSetup,
    setSidebarOpen,
  }), [toasts, isSetup, darkMode, autoRefresh, sidebarOpen])

  return (
    <AppContext.Provider value={value}>
      {children}
      <EuiGlobalToastList
        toasts={toasts}
        dismissToast={dismissToast}
        toastLifeTimeMs={10000}
      />
    </AppContext.Provider>
  );
}