/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect } from 'react'
import { Router, Route, Switch } from 'react-router-dom'
import { EuiProvider } from '@elastic/eui'
import { useAppContext } from './Contexts/AppContext'
import { ResourceProvider } from './Contexts/ResourceContext'
import { Pages } from './Pages'
import { Chat } from './Layout'
import history from './history'

/**
 * Custom route component that redirects to the home page to finish setup
 * if setup isn't complete.
 */
const RouteWithSetupCheck = ({ component: Component, render, ...rest }) => {
  const { isSetup, addToast } = useAppContext()
  const shouldRedirect = isSetup === false && history.location.pathname !== '/'

  useEffect(() => {
    if (shouldRedirect) {
      addToast({ color: 'warning', title: `Setup isn't complete` })
      history.push('/')
    }
  }, [shouldRedirect])

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

const Routes = () => {

  const title = 'Elasticsearch Relevance Studio'
  const { darkMode } = useAppContext()

  return (
    <EuiProvider colorMode={darkMode ? 'dark' : 'light'}>
      <Router history={history}>
        <Route path={[
          '/workspaces/:workspace_id/benchmarks/:benchmark_id/evaluations/:evaluation_id',
          '/workspaces/:workspace_id/benchmarks/:benchmark_id',
          '/workspaces/:workspace_id/strategies/:strategy_id',
          '/workspaces/:workspace_id/displays/:display_id',
          '/workspaces/:workspace_id',
          '/',
        ]}>
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
        </Route>
      </Router>
    </EuiProvider>
  )
}

export default Routes