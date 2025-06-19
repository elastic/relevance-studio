import React from 'react'
import { AppProvider } from './Contexts/AppContext'
import Routes from './Routes'

/**
 * Configure Monaco editors to use local web workers instead of the CDN.
 * Each language label (e.g., 'json', 'markdown') maps to a local worker script
 * under /monaco-editor/min. Markdown uses the default: editor.worker.js.
 */
if (!window.MonacoEnvironment) {
  window.MonacoEnvironment = {
    getWorkerUrl: (moduleId, label) => {
      switch (label) {
        case 'json':
          return URL.createObjectURL(
            new Blob([
              `importScripts('/monaco-editor/min/vs/language/json/json.worker.js');`
            ], { type: 'text/javascript' })
          )
        default:
          return URL.createObjectURL(
            new Blob([
              `importScripts('/monaco-editor/min/vs/editor/editor.worker.js');`
            ], { type: 'text/javascript' })
          )
      }
    }
  }
}

const App = () => {
  return (
    <AppProvider>
      <Routes />
    </AppProvider>
  )
}

export default App