import React from 'react'
import { HashRouter as Router, Redirect, Route, Switch } from 'react-router-dom'
import { ProjectProvider } from './Contexts/ProjectContext'
import { Pages } from './Pages'

const Routes = () => {

  const title = 'ESRE Evaluation Framework'

  return (
    <Router>
      <ProjectProvider>
        <Switch>
          <Route path='/' exact render={(e) => {
            document.title = title
            return <Redirect to='/projects' /> // TODO: Implement <Pages.Home />
          }} />
          <Route path='/projects' exact render={(r) => {
            document.title = `Projects - ${title}`
            return <Pages.Projects />
          }} />
          <Route path='/projects/:project_id/displays' exact render={(r) => {
            document.title = `Displays - ${title}`
            return <Pages.Displays />
          }} />
          <Route path='/projects/:project_id/displays/:display_id' render={(r) => {
            document.title = `Displays - ${r.match.params.display_id} -  ${title}`
            return <Pages.DisplaysEdit />
          }} />
          <Route path='/projects/:project_id/judgements' exact render={(r) => {
            document.title = `Judgements - ${title}`
            return <Pages.Judgements />
          }} />
          <Route path='/projects/:project_id/scenarios' exact render={(r) => {
            document.title = `Scenarios - ${title}`
            return <Pages.Scenarios />
          }} />
          <Route path='/projects/:project_id/strategies' exact render={(r) => {
            document.title = `Strategies - ${title}`
            return <Pages.Strategies />
          }} />
          <Route path='/projects/:project_id/strategies/:strategy_id' render={(r) => {
            document.title = `Strategies - ${r.match.params.strategy_id} - ${title}`
            return <Pages.StrategiesEdit />
          }} />
          <Route path='/projects/:project_id/evaluations' exact render={(r) => {
            document.title = `Evaluations - ${title}`
            return <Pages.Evaluations />
          }} />
          <Route path='/projects/:project_id/evaluations/:evaluation_id' render={(r) => {
            document.title = `Evaluations - ${r.match.params.evaluation_id} - ${title}`
            return <Pages.EvaluationsView />
          }} />
          <Route path='*' render={(r) => {
            document.title = `Not Found - ${title}`
            return <>Not Found</>
          }} />
        </Switch>
      </ProjectProvider>
    </Router>
  )
}

export default Routes