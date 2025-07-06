import { useEffect, useState, useMemo } from 'react'
import { useRouteMatch } from 'react-router-dom'
import { EuiBreadcrumbs, EuiSkeletonRectangle } from '@elastic/eui'
import { usePageResources, useResources } from '../Contexts/ResourceContext'

const Breadcrumbs = () => {
  const { path, url } = useRouteMatch()
  const [breadcrumbs, setBreadcrumbs] = useState([])

  // Safely get resources and loading states
  let resources = {}
  let isLoading = () => false
  try {
    resources = usePageResources()
    const resourceContext = useResources()
    isLoading = resourceContext.isLoading
  } catch (error) {
    // No ResourceProvider available (like on home page)
    resources = {}
  }

  // Memoize resources to prevent infinite loops
  const memoizedResources = useMemo(() => resources, [JSON.stringify(resources)])

  // Check if we're waiting for any required resources to load
  const getRequiredResourceTypes = (routePath, routeUrl) => {
    const parts = routePath.split('/').filter(Boolean)
    const requiredTypes = []

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      if (part.startsWith(':') && part.endsWith('_id')) {
        const resourceType = part.slice(1).replace('_id', '')
        requiredTypes.push(resourceType)
      }
    }

    return requiredTypes
  }

  const requiredResourceTypes = getRequiredResourceTypes(path, url)

  // Check which resources are available vs still loading
  const getResourceStatus = () => {
    const status = {}
    requiredResourceTypes.forEach(type => {
      status[type] = {
        available: !!memoizedResources[type],
        loading: isLoading(type)
      }
    })
    return status
  }

  const resourceStatus = getResourceStatus()

  // Only wait if we need resources but none are loaded AND none are loading (initial problematic state)
  const hasAnyRequiredResources = requiredResourceTypes.some(type => memoizedResources[type])
  const hasAnyLoadingResources = requiredResourceTypes.some(type => isLoading(type))
  const shouldWaitForInitialLoad = requiredResourceTypes.length > 0 &&
    !hasAnyRequiredResources && !hasAnyLoadingResources

  useEffect(() => {
    // Only wait on initial load when no resources are available
    if (shouldWaitForInitialLoad)
      return

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
    if (parts.length > 0) {
      homeCrumb.href = '#/'
    }
    const crumbs = [homeCrumb]
    let accumulated = '#'
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const value = urlParts[i]
      if (part.startsWith(':')) {
        const paramName = part.slice(1)
        let label = value

        // Dynamically get friendly name from any resource type
        if (paramName.endsWith('_id')) {
          const resourceType = paramName.replace('_id', '') // project_id -> project
          const resource = memoizedResources[resourceType]

          if (resource) {
            // Use resource.name if available, otherwise fall back to resource._id, then to the URL value
            label = resource.name || resource._id || value
          } else if (resourceStatus[resourceType]?.loading ||
            (requiredResourceTypes.includes(resourceType) && !resourceStatus[resourceType]?.available)) {
            // Resource is loading OR should be loading (required but not available)
            label = (<EuiSkeletonRectangle height={18} width={150} />)
          } else {
            // Resource not available and not loading, use URL value
            label = value
          }
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
  }, [path, url, memoizedResources, shouldWaitForInitialLoad, JSON.stringify(resourceStatus)])

  // Only hide breadcrumbs on initial load when no resources are available
  if (shouldWaitForInitialLoad)
    return null

  return (
    <EuiBreadcrumbs breadcrumbs={breadcrumbs} max={0} truncate={false} />
  )
}

export default Breadcrumbs