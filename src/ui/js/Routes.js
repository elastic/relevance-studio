import { useContext, useEffect } from 'react'
import { Router, Route, Switch } from 'react-router-dom'
import { AppContext } from './Contexts/AppContext'
import { ProjectProvider } from './Contexts/ProjectContext'
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

const ProjectContextRoute = ({ children }) => (
  <ProjectProvider>{children}</ProjectProvider>
)

const Routes = () => {

  const title = 'Elasticsearch Relevance Studio'

  return (
    <Router history={history}>
      <Switch>
        <Route path='/' exact render={(e) => {
          document.title = title
          return <Pages.Home />
        }} />
        <RouteWithSetupCheck path='/projects' exact render={(r) => {
          document.title = `Projects - ${title}`
          return <Pages.Projects />
        }} />

        {/* Project-scoped routes */}
        <Route path='/projects/:project_id'>
          <ProjectContextRoute>
            <Switch>
              <RouteWithSetupCheck path='/projects/:project_id/displays' exact render={() => {
                document.title = `Displays - ${title}`
                return <Pages.Displays />
              }} />
              <RouteWithSetupCheck path='/projects/:project_id/displays/:display_id' render={(r) => {
                document.title = `Displays - ${r.match.params.display_id} - ${title}`
                return <Pages.DisplaysEdit />
              }} />
              <RouteWithSetupCheck path='/projects/:project_id/judgements' exact render={() => {
                document.title = `Judgements - ${title}`
                return <Pages.Judgements />
              }} />
              <RouteWithSetupCheck path='/projects/:project_id/scenarios' exact render={() => {
                document.title = `Scenarios - ${title}`
                return <Pages.Scenarios />
              }} />
              <RouteWithSetupCheck path='/projects/:project_id/strategies' exact render={() => {
                document.title = `Strategies - ${title}`
                return <Pages.Strategies />
              }} />
              <RouteWithSetupCheck path='/projects/:project_id/strategies/:strategy_id' render={(r) => {
                document.title = `Strategies - ${r.match.params.strategy_id} - ${title}`
                return <Pages.StrategiesEdit />
              }} />
              <RouteWithSetupCheck path='/projects/:project_id/benchmarks' exact render={() => {
                document.title = `Benchmarks - ${title}`
                return <Pages.Benchmarks />
              }} />
              <RouteWithSetupCheck path='/projects/:project_id/benchmarks/:benchmark_id' exact render={(r) => {
                document.title = `Benchmarks - ${r.match.params.benchmark_id} - ${title}`
                return <Pages.BenchmarksView />
              }} />
              <RouteWithSetupCheck path='/projects/:project_id/benchmarks/:benchmark_id/evaluations/:evaluation_id' render={(r) => {
                document.title = `Evaluations - ${r.match.params.evaluation_id} - ${title}`
                return <Pages.EvaluationsView />
              }} />
            </Switch>
          </ProjectContextRoute>
        </Route>

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