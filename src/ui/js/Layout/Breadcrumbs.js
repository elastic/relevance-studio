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
    const _breadcrumbs = [{ text: 'Home', href: '#/' }]
    const parts = path.split('/').filter(Boolean)
    const urlParts = url.split('/').filter(Boolean)
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
        accumulated += `/${value}`
        _breadcrumbs.push({ text: label, href: accumulated })
      } else {
        accumulated += `/${part}`
        const label = part.charAt(0).toUpperCase() + part.slice(1)
        _breadcrumbs.push({ text: label, href: accumulated })
      }
    }
    setBreadcrumbs(_breadcrumbs)
  }, [path, url, project])

  return (
    <EuiBreadcrumbs
      breadcrumbs={breadcrumbs}
      truncate={false}
    />
  )
}

export default Breadcrumbs