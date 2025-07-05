// ResourceContext.js
import { createContext, useContext, useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api'

const ResourceContext = createContext()

// Define resource loaders
const RESOURCE_LOADERS = {
  project: (params) => api.projects_get(params.project_id),
  benchmark: (params) => api.benchmarks_get(params.project_id, params.benchmark_id),
  evaluation: (params) => api.evaluations_get(params.project_id, params.benchmark_id, params.evaluation_id),
  display: (params) => api.displays_get(params.project_id, params.display_id),
  strategy: (params) => api.strategies_get(params.project_id, params.strategy_id),
  scenario: (params) => api.scenarios_get(params.project_id, params.scenario_id),
}

// Map param names to resource types
const PARAM_TO_RESOURCE = {
  project_id: 'project',
  benchmark_id: 'benchmark',
  evaluation_id: 'evaluation',
  display_id: 'display',
  strategy_id: 'strategy',
  scenario_id: 'scenario',
}

export const ResourceProvider = ({ children }) => {
  const params = useParams()
  const [state, setState] = useState({
    resources: {},
    loading: {},
    errors: {}
  })

  useEffect(() => {
    const loadResources = async () => {

      // Determine which resources to load
      const resourcesToLoad = []
      Object.keys(params).forEach(paramName => {
        const resourceType = PARAM_TO_RESOURCE[paramName]
        if (resourceType && RESOURCE_LOADERS[resourceType]) {
          resourcesToLoad.push(resourceType)
        }
      })

      if (resourcesToLoad.length === 0) {
        setState({ resources: {}, loading: {}, errors: {} })
        return
      }

      // Keep resources that are still relevant
      const currentResources = { ...state.resources }
      const currentLoading = { ...state.loading }
      const currentErrors = { ...state.errors }

      // Remove resources that are no longer needed
      Object.keys(currentResources).forEach(resourceType => {
        if (!resourcesToLoad.includes(resourceType)) {
          delete currentResources[resourceType]
          delete currentLoading[resourceType]
          delete currentErrors[resourceType]
        }
      })

      // Determine which resources actually need to be loaded (not already available)
      const resourcesToFetch = resourcesToLoad.filter(resourceType => {
        return !currentResources[resourceType]
      })

      if (resourcesToFetch.length === 0) {
        setState({
          resources: currentResources,
          loading: currentLoading,
          errors: currentErrors
        })
        return
      }

      // Set loading state for new resources only
      resourcesToFetch.forEach(resourceType => {
        currentLoading[resourceType] = true
        delete currentErrors[resourceType] // Clear any previous errors
      })

      setState({
        resources: currentResources,
        loading: currentLoading,
        errors: currentErrors
      })

      // Load only the new resources
      const results = await Promise.allSettled(
        resourcesToFetch.map(async (type) => {
          try {
            const response = await RESOURCE_LOADERS[type](params)
            const data = { ...response.data._source, _id: response.data._id }
            return { type, data, success: true }
          } catch (error) {
            return { type, error, success: false }
          }
        })
      )

      // Update state with newly loaded resources
      const finalResources = { ...currentResources }
      const finalLoading = { ...currentLoading }
      const finalErrors = { ...currentErrors }

      results.forEach((result, index) => {
        const type = resourcesToFetch[index]
        finalLoading[type] = false

        if (result.status === 'fulfilled' && result.value.success) {
          finalResources[type] = result.value.data
        } else {
          finalErrors[type] = result.value?.error || result.reason
        }
      })

      setState({
        resources: finalResources,
        loading: finalLoading,
        errors: finalErrors
      })
    }

    loadResources()
  }, [JSON.stringify(params)])

  const value = {
    ...state,
    // Dynamic accessors
    isLoading: (type) => state.loading[type] || false,
    hasError: (type) => !!state.errors[type],
    getError: (type) => state.errors[type] || null,
    // Convenience flags
    isAnyLoading: Object.values(state.loading).some(Boolean),
    hasAnyError: Object.keys(state.errors).length > 0
  }

  return (
    <ResourceContext.Provider value={value}>
      {children}
    </ResourceContext.Provider>
  )
}

// Main hook to use resources
export const useResources = () => {
  const context = useContext(ResourceContext)
  if (!context) {
    throw new Error('useResources must be used within a ResourceProvider')
  }
  return context
}

// Convenience hook that just returns the resources object
export const usePageResources = () => {
  const { resources } = useResources()
  return resources
}