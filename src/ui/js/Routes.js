/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect } from 'react'
import { Router, Route, Switch, useLocation } from 'react-router-dom'
import { EuiProvider } from '@elastic/eui'
import { useAppContext } from './Contexts/AppContext'
import { useAuthContext } from './Contexts/AuthContext'
import { ResourceProvider } from './Contexts/ResourceContext'
import { Pages } from './Pages'
import { Chat } from './Layout'
import Login from './components/Login'
import history from './history'

const title = 'Elasticsearch Relevance Studio'

/**
 * Auth guard: redirect to /login when not authenticated.
 * Only wraps protected routes; /login is rendered outside.
 */
export const AuthGuard = ({ children }) => {
  const { isAuthenticated, hasCheckedSession, isLoading } = useAuthContext()
  const location = useLocation()

  if (isLoading || !hasCheckedSession) {
    return null
  }
  if (!isAuthenticated) {
    history.replace(`/login?next=${encodeURIComponent(location.pathname)}`)
    return null
  }
  return children
}

/**
 * Logout route: signs the user out and redirects to /login.
 */
const LogoutRoute = () => {
  const { logout, hasCheckedSession, isLoading } = useAuthContext()

  useEffect(() => {
    if (!isLoading && hasCheckedSession) {
      logout()
    }
  }, [isLoading, hasCheckedSession])

  return null
}

/**
 * Login route wrapper: redirect authenticated users away from /login.
 */
const LoginRoute = () => {
  const { isAuthenticated, hasCheckedSession, isLoading } = useAuthContext()
  const location = useLocation()

  if (isLoading || !hasCheckedSession) {
    return null
  }
  if (isAuthenticated) {
    const params = new URLSearchParams(location.search)
    const next = params.get('next') || '/'
    history.replace(next)
    return null
  }
  document.title = `Sign in - ${title}`
  return <Login />
}

/**
 * Custom route component that redirects to the home page to finish setup
 * if setup isn't complete.
 */
const RouteWithSetupCheck = ({ component: Component, render, ...rest }) => {
  const { isSetup, isUpgradeNeeded, addToast } = useAppContext()
  const shouldRedirect = (isSetup === false || isUpgradeNeeded === true) && history.location.pathname !== '/'

  useEffect(() => {
    if (shouldRedirect) {
      if (isSetup === false) {
        addToast({ color: 'warning', title: `Setup isn't complete` })
      } else {
        addToast({ color: 'warning', title: 'Upgrade required' })
      }
      history.push('/')
    }
  }, [shouldRedirect, isSetup])

  return (
    <Route
      {...rest}
      render={(props) => {
        if (isSetup === undefined || shouldRedirect) return null
        return Component ? <Component {...props} /> : render(props)
      }}
    />
  )
}

const allOtherPaths = [
  '/workspaces/:workspace_id/benchmarks/:benchmark_id/evaluations/:evaluation_id',
  '/workspaces/:workspace_id/benchmarks/:benchmark_id',
  '/workspaces/:workspace_id/strategies/:strategy_id',
  '/workspaces/:workspace_id/displays/:display_id',
  '/workspaces/:workspace_id',
  '/',
]

const Routes = () => {
  const { darkMode } = useAppContext()

  return (
    <EuiProvider colorMode={darkMode ? 'dark' : 'light'}>
      <Router history={history}>
        <Switch>
          {/* Auth routes - outside AuthGuard and ResourceProvider to avoid 401 redirect loops */}
          <Route path='/login' exact render={() => <LoginRoute />} />
          <Route path='/logout' exact render={() => <LogoutRoute />} />

          {/* All other routes - inside AuthGuard and ResourceProvider */}
          <Route path={allOtherPaths}>
            <AuthGuard>
              <ResourceProvider>
                <Switch>
                  {/* Home route */}
                  <Route path='/' exact render={(e) => {
                    document.title = title
                    return <Pages.Home />
                  }} />
                  <RouteWithSetupCheck path='/workspaces' exact render={(r) => {
                    document.title = `Workspaces - ${title}`
                    return <Pages.Workspaces />
                  }} />

                  {/* Resource routes */}
                  <RouteWithSetupCheck path='/workspaces/:workspace_id' exact render={(r) => {
                    document.title = `Workspaces - ${r.match.params.workspace_id} - ${title}`
                    return <Pages.WorkspacesView />
                  }} />
                  <RouteWithSetupCheck path='/workspaces/:workspace_id/displays' exact render={() => {
                    document.title = `Displays - ${title}`
                    return <Pages.Displays />
                  }} />
                  <RouteWithSetupCheck path='/workspaces/:workspace_id/displays/:display_id' exact render={(r) => {
                    document.title = `Displays - ${r.match.params.display_id} - ${title}`
                    return <Pages.DisplaysEdit />
                  }} />
                  <RouteWithSetupCheck path='/workspaces/:workspace_id/judgements' exact render={() => {
                    document.title = `Judgements - ${title}`
                    return <Pages.Judgements />
                  }} />
                  <RouteWithSetupCheck path='/workspaces/:workspace_id/scenarios' exact render={() => {
                    document.title = `Scenarios - ${title}`
                    return <Pages.Scenarios />
                  }} />
                  <RouteWithSetupCheck path='/workspaces/:workspace_id/strategies' exact render={() => {
                    document.title = `Strategies - ${title}`
                    return <Pages.Strategies />
                  }} />
                  <RouteWithSetupCheck path='/workspaces/:workspace_id/strategies/:strategy_id' exact render={(r) => {
                    document.title = `Strategies - ${r.match.params.strategy_id} - ${title}`
                    return <Pages.StrategiesEdit />
                  }} />
                  <RouteWithSetupCheck path='/workspaces/:workspace_id/benchmarks' exact render={() => {
                    document.title = `Benchmarks - ${title}`
                    return <Pages.Benchmarks />
                  }} />
                  <RouteWithSetupCheck path='/workspaces/:workspace_id/benchmarks/:benchmark_id' exact render={(r) => {
                    document.title = `Benchmarks - ${r.match.params.benchmark_id} - ${title}`
                    return <Pages.BenchmarksView />
                  }} />
                  <RouteWithSetupCheck path='/workspaces/:workspace_id/benchmarks/:benchmark_id/evaluations' exact render={(r) => {
                    document.title = `Benchmarks - ${r.match.params.benchmark_id} - ${title}`
                    return <Pages.BenchmarksView />
                  }} />
                  <RouteWithSetupCheck path='/workspaces/:workspace_id/benchmarks/:benchmark_id/evaluations/:evaluation_id' exact render={(r) => {
                    document.title = `Evaluations - ${r.match.params.evaluation_id} - ${title}`
                    return <Pages.EvaluationsView />
                  }} />

                  {/* Fallback route */}
                  <Route path='*' render={(r) => {
                    document.title = `Not Found - ${title}`
                    return <Pages.NotFound />
                  }} />
                </Switch>
                <Chat />
              </ResourceProvider>
            </AuthGuard>
          </Route>
        </Switch>
      </Router>
    </EuiProvider>
  )
}

export default Routes
