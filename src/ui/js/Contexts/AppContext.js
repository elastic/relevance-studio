/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
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

  const [deploymentMode, setDeploymentMode] = useState(null)
  const [hasCheckedSetup, setHasCheckedSetup] = useState(false)
  const [isCheckingSetup, setIsCheckingSetup] = useState(false)
  const [isSetup, setIsSetup] = useState(null)
  const [licenseType, setLicenseType] = useState(null)
  const [licenseStatus, setLicenseStatus] = useState(null)

  // Local storage state
  const [autoRefresh, setAutoRefresh] = useState(() => {
    const val = localStorage.getItem('autoRefresh')
    return val === null ? true : val === 'true' // defaults to true
  })
  const [darkMode, setDarkMode] = useState(() => {
    const val = localStorage.getItem('darkMode')
    return val === null ? false : val === 'true'; // defaults to false
  })
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const val = localStorage.getItem('sidebarOpen')
    return val === null ? false : val === 'true'; // defaults to false
  })
  useEffect(() => localStorage.setItem('autoRefresh', autoRefresh), [autoRefresh])
  useEffect(() => localStorage.setItem('darkMode', darkMode), [darkMode])
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

  // Check setup & deployment info
  useEffect(() => {
    const initApp = async () => {
      setIsCheckingSetup(true)
      try {
        const response = await api.setup_check()

        // Deployment info
        setDeploymentMode(response?.data?.deployment?.mode)
        setLicenseType(response?.data?.deployment?.license?.type)
        setLicenseStatus(response?.data?.deployment?.license?.status)

        // Setup status
        if ((response?.data?.setup?.failures ?? 0) > 0) {
          setIsSetup(false)
        } else {
          setIsSetup(true)
        }
      } catch (e) {
        console.error('Failed to initialize app:', e)
        setIsSetup(false)
        setDeploymentMode(null)
        setLicenseType(null)
        setLicenseStatus(null)
      } finally {
        setIsCheckingSetup(false)
        setHasCheckedSetup(true)
      }
    }
    initApp()
  }, [])

  const value = useMemo(() => ({
    addToast,
    autoRefresh,
    darkMode,
    deploymentMode,
    hasCheckedSetup,
    isCheckingSetup,
    licenseType,
    licenseStatus,
    isSetup,
    sidebarOpen,
    setAutoRefresh,
    setDarkMode,
    setDeploymentMode,
    setLicenseType,
    setLicenseStatus,
    setIsSetup,
    setSidebarOpen,
  }), [
    toasts,
    isSetup,
    darkMode,
    autoRefresh,
    deploymentMode,
    hasCheckedSetup,
    isCheckingSetup,
    licenseType,
    licenseStatus,
    sidebarOpen,
    setAutoRefresh,
  ])

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