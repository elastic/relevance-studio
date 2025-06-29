/**
 * Monaco Editor uses Web Workers to power language features like code folding,
 * syntax validation, and auto-completion. By default, it tries to load these
 * worker scripts from a CDN or expects a bundler (like Webpack with a Monaco
 * plugin) to handle them automatically.
 *
 * Since we're self-hosting Monaco and copying the raw `monaco-editor/min` files
 * into our `dist/` directory, Monaco doesn't know where to find its workers.
 * Without this `MonacoEnvironment.getWorkerUrl` override, Monaco fails to load
 * the necessary workers — which silently disables folding and other features.
 *
 * This block tells Monaco where to find the worker scripts locally.
 * It's required whenever Monaco is used without a bundler plugin that
 * automatically wires up the workers (e.g. `monaco-editor-webpack-plugin`).
 * 
 * However, it doesn't seem to be working completely. Code folding doesn't work
 * with this code block uncommented, which is symptomatic that it's not working
 * as expected. So I'm leaving it commeted out for now.
 */

/*
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
*/

import { AppProvider } from './Contexts/AppContext'
import Routes from './Routes'

const App = () => {
  return (
    <AppProvider>
      <Routes />
    </AppProvider>
  )
}

export default App