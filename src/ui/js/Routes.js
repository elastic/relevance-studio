import { useContext, useEffect } from 'react'
import { Router, Route, Switch } from 'react-router-dom'
import { AppContext } from './Contexts/AppContext'
import { ResourceProvider } from './Contexts/ResourceContext'
import { Pages } from './Pages'
import history from './history'

/**
 * Custom route component that redirects to the home page to finish setup
 * if setup isn't complete.
 */
const RouteWithSetupCheck = ({ component: Component, render, ...rest }) => {
  const { isSetup, addToast } = useContext(AppContext)
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

  return (
    <Router history={history}>
      <Switch>

        {/* Home route */}
        <Route path='/' exact render={(e) => {
          document.title = title
          return <Pages.Home />
        }} />
        <RouteWithSetupCheck path='/projects' exact render={(r) => {
          document.title = `Projects - ${title}`
          return <Pages.Projects />
        }} />

        {/* Resource routes - wrap only the ones that need resources */}
        <RouteWithSetupCheck path='/projects/:project_id' exact render={(r) => {
          document.title = `Projects - ${r.match.params.project_id} - ${title}`
          return <ResourceProvider><Pages.ProjectsView /></ResourceProvider>
        }} />
        <RouteWithSetupCheck path='/projects/:project_id/displays' exact render={() => {
          document.title = `Displays - ${title}`
          return <ResourceProvider><Pages.Displays /></ResourceProvider>
        }} />
        <RouteWithSetupCheck path='/projects/:project_id/displays/:display_id' exact render={(r) => {
          document.title = `Displays - ${r.match.params.display_id} - ${title}`
          return <ResourceProvider><Pages.DisplaysEdit /></ResourceProvider>
        }} />
        <RouteWithSetupCheck path='/projects/:project_id/judgements' exact render={() => {
          document.title = `Judgements - ${title}`
          return <ResourceProvider><Pages.Judgements /></ResourceProvider>
        }} />
        <RouteWithSetupCheck path='/projects/:project_id/scenarios' exact render={() => {
          document.title = `Scenarios - ${title}`
          return <ResourceProvider><Pages.Scenarios /></ResourceProvider>
        }} />
        <RouteWithSetupCheck path='/projects/:project_id/strategies' exact render={() => {
          document.title = `Strategies - ${title}`
          return <ResourceProvider><Pages.Strategies /></ResourceProvider>
        }} />
        <RouteWithSetupCheck path='/projects/:project_id/strategies/:strategy_id' exact render={(r) => {
          document.title = `Strategies - ${r.match.params.strategy_id} - ${title}`
          return <ResourceProvider><Pages.StrategiesEdit /></ResourceProvider>
        }} />
        <RouteWithSetupCheck path='/projects/:project_id/benchmarks' exact render={() => {
          document.title = `Benchmarks - ${title}`
          return <ResourceProvider><Pages.Benchmarks /></ResourceProvider>
        }} />
        <RouteWithSetupCheck path='/projects/:project_id/benchmarks/:benchmark_id' exact render={(r) => {
          document.title = `Benchmarks - ${r.match.params.benchmark_id} - ${title}`
          return <ResourceProvider><Pages.BenchmarksView /></ResourceProvider>
        }} />
        <RouteWithSetupCheck path='/projects/:project_id/benchmarks/:benchmark_id/evaluations/:evaluation_id' exact render={(r) => {
          document.title = `Evaluations - ${r.match.params.evaluation_id} - ${title}`
          return <ResourceProvider><Pages.EvaluationsView /></ResourceProvider>
        }} />

        {/* Fallback route */}
        <Route path='*' render={(r) => {
          document.title = `Not Found - ${title}`
          return <Pages.NotFound />
        }} />
      </Switch>
    </Router>
  )
}

export default Routes