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
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const val = localStorage.getItem('sidebarOpen')
    return val === null ? true : val === 'true' // defaults to true
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

  // Check setup
  const [isSetup, setIsSetup] = useState(null)

  // Check if setup is complete
  useEffect(() => {
    const checkSetup = async () => {
      try {
        const response = await api.setup_check()
        if ((response?.data?.failures ?? 0) > 0) {
          setIsSetup(false) // just update state
        } else {
          setIsSetup(true)
        }
      } catch (e) {
        console.error(e)
        setIsSetup(false)
      }
    }
    checkSetup()
  }, [])

  const value = useMemo(() => ({
    addToast,
    autoRefresh,
    darkMode,
    isSetup,
    sidebarOpen,
    setAutoRefresh,
    setDarkMode,
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