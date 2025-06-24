import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useMemo
} from 'react'
import { EuiGlobalToastList } from '@elastic/eui'

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
  const [toasts, setToasts] = useState([])
  useEffect(() => localStorage.setItem('autoRefresh', autoRefresh), [autoRefresh])
  useEffect(() => localStorage.setItem('darkMode', darkMode), [darkMode])

  // Toasts
  const addToast = (toast) => {
    toast.id = `${Date.now()}-${Math.random()}`;
    setToasts(toasts.concat(toast))
  }
  const dismissToast = (removedToast) => {
    setToasts((toasts) => toasts.filter((toast) => toast.id !== removedToast.id))
  }

  // Make addToast globally available
  useEffect(() => {
    _appContext = { addToast }
    return () => { _appContext = null }
  }, [addToast])

  const value = useMemo(() => ({
    addToast,
    autoRefresh,
    darkMode,
    setAutoRefresh,
    setDarkMode,
  }), [toasts, darkMode, autoRefresh])

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