import { useEffect, useState } from 'react'
import { useRouteMatch } from 'react-router-dom'
import { EuiBreadcrumbs } from '@elastic/eui'
import { useProjectContext } from '../Contexts/ProjectContext'

const Breadcrumbs = () => {

  const { path, url } = useRouteMatch()

  ////  Context  ///////////////////////////////////////////////////////////////

  const projectContext = useProjectContext()
  const project = projectContext?.project

  ////  State  /////////////////////////////////////////////////////////////////

  const [breadcrumbs, setBreadcrumbs] = useState([])

  ////  Render  ////////////////////////////////////////////////////////////////

  useEffect(() => {
    // Breadcrumbs for the NotFound route
    if (path === '*') {
      setBreadcrumbs([
        { text: 'Home', href: '#/' },
        { text: 'Not Found' }
      ])
      return
    }
    // Breadcrumbs for all other routes
    const parts = path.split('/').filter(Boolean)
    const urlParts = url.split('/').filter(Boolean)
    const homeCrumb = { text: 'Home' }
    if (parts.length > 0)
      homeCrumb.href = '#/'
    const crumbs = [ homeCrumb ]
    let accumulated = '#'
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const value = urlParts[i]
      if (part.startsWith(':')) {
        const paramName = part.slice(1)
        let label = value
        if (paramName === 'project_id') {
          if (!project?.name) // project context hasn't fully loaded
            return // return to prevent flicker
          label = project?.name || value
        }
        const crumb = { text: label }
        if (i + 1 < parts.length) {
          accumulated += `/${value}`
          crumb.href = accumulated
        }
        crumbs.push(crumb)
      } else {
        const label = part.charAt(0).toUpperCase() + part.slice(1)
        const crumb = { text: label }
        if (i + 1 < parts.length) {
          accumulated += `/${part}`
          crumb.href = accumulated
        }
        crumbs.push(crumb)
      }
    }
    setBreadcrumbs(crumbs)
  }, [path, url, project])

  return (
    <EuiBreadcrumbs
      breadcrumbs={breadcrumbs}
      truncate={false}
    />
  )
}

export default Breadcrumbs