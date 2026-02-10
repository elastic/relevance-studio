/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { createContext, useCallback, useContext, useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api'
import utils from '../utils'

const ResourceContext = createContext()

// Define how to request resources
const RESOURCE_LOADERS = {

  // Individual resources (by _id)
  workspace: (params) => api.workspaces_get(params.workspace_id),
  benchmark: (params) => api.benchmarks_get(params.workspace_id, params.benchmark_id),
  evaluation: (params) => api.evaluations_get(params.workspace_id, params.benchmark_id, params.evaluation_id),
  display: (params) => api.displays_get(params.workspace_id, params.display_id),
  strategy: (params) => api.strategies_get(params.workspace_id, params.strategy_id),
  scenario: (params) => api.scenarios_get(params.workspace_id, params.scenario_id),

  // Collection resources (e.g. search results)
  displays: (params) => api.displays_search(params.workspace_id, { text: '*' }),
}

// Define how to extract resources from the responses
const RESOURCE_DATA_EXTRACTORS = {

  // Individual resources (by _id)
  workspace: (response) => ({ ...response.data._source, _id: response.data._id }),
  benchmark: (response) => ({ ...response.data._source, _id: response.data._id }),
  evaluation: (response) => ({ ...response.data._source, _id: response.data._id }),
  display: (response) => ({ ...response.data._source, _id: response.data._id }),
  strategy: (response) => ({ ...response.data._source, _id: response.data._id }),
  scenario: (response) => ({ ...response.data._source, _id: response.data._id }),
  
  // Collection resources (e.g. search results)
  displays: (response) => utils.hitsToDocs(response)
}

// Map param names to resource types
const PARAM_TO_RESOURCE = {
  workspace_id: 'workspace',
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
  const [additionalResources, setAdditionalResources] = useState([])

  // Method for components to request additional resources
  const requestAdditionalResources = useCallback((resources) => {
    setAdditionalResources(prev => {
      const newResources = [...new Set([...prev, ...resources])]
      return newResources
    })
  }, [])

  // Method to update a specific resource
  const setResource = useCallback((resourceType, resourceData) => {
    setState(prevState => ({
      ...prevState,
      resources: {
        ...prevState.resources,
        [resourceType]: resourceData
      }
    }))
  }, [])

  // Method to update a specific resource in a collection (for arrays like displays)
  const updateResourceInCollection = useCallback((resourceType, resourceId, updatedData) => {
    setState(prevState => {
      const currentCollection = prevState.resources[resourceType]
      if (!Array.isArray(currentCollection)) {
        console.warn(`Resource ${resourceType} is not a collection`)
        return prevState
      }

      const updatedCollection = currentCollection.map(item => 
        item._id === resourceId ? { ...item, ...updatedData } : item
      )

      return {
        ...prevState,
        resources: {
          ...prevState.resources,
          [resourceType]: updatedCollection
        }
      }
    })
  }, [])

  // Method to add a resource to a collection
  const addResourceToCollection = useCallback((resourceType, resourceData) => {
    setState(prevState => {
      const currentCollection = prevState.resources[resourceType]
      if (!Array.isArray(currentCollection)) {
        console.warn(`Resource ${resourceType} is not a collection`)
        return prevState
      }

      return {
        ...prevState,
        resources: {
          ...prevState.resources,
          [resourceType]: [...currentCollection, resourceData]
        }
      }
    })
  }, [])

  // Method to remove a resource from a collection
  const removeResourceFromCollection = useCallback((resourceType, resourceId) => {
    setState(prevState => {
      const currentCollection = prevState.resources[resourceType]
      if (!Array.isArray(currentCollection)) {
        console.warn(`Resource ${resourceType} is not a collection`)
        return prevState
      }

      const filteredCollection = currentCollection.filter(item => item._id !== resourceId)

      return {
        ...prevState,
        resources: {
          ...prevState.resources,
          [resourceType]: filteredCollection
        }
      }
    })
  }, [])

  // Load resources when params change
  useEffect(() => {
    const loadResources = async () => {
      console.debug('🚀 Params changed:', params)
      console.debug('📎 Additional resources requested:', additionalResources)

      // Combine URL-based and additional resources
      const urlResources = []
      Object.keys(params).forEach(paramName => {
        const resourceType = PARAM_TO_RESOURCE[paramName]
        if (resourceType && RESOURCE_LOADERS[resourceType]) {
          urlResources.push(resourceType)
        }
      })

      const allResourcesToLoad = [...new Set([...urlResources, ...additionalResources])]

      if (allResourcesToLoad.length === 0) {
        setState({ resources: {}, loading: {}, errors: {} })
        return
      }
      console.debug('📋 Resources to load:', allResourcesToLoad)

      // Keep resources that are still relevant
      const currentResources = { ...state.resources }
      const currentLoading = { ...state.loading }
      const currentErrors = { ...state.errors }

      // Remove resources that are no longer needed
      Object.keys(currentResources).forEach(resourceType => {
        if (!allResourcesToLoad.includes(resourceType)) {
          console.debug(`🗑️ Removing ${resourceType} (no longer needed)`)
          delete currentResources[resourceType]
          delete currentLoading[resourceType]
          delete currentErrors[resourceType]
        }
      })

      // Determine which resources actually need to be loaded (not already available or ID mismatch)
      const resourcesToFetch = allResourcesToLoad.filter(resourceType => {
        const currentResource = currentResources[resourceType]
        if (!currentResource) return true

        // 1. Check if this specific resource's ID has changed in the URL
        const idParamName = Object.keys(PARAM_TO_RESOURCE).find(key => PARAM_TO_RESOURCE[key] === resourceType)
        if (idParamName && params[idParamName] && currentResource._id !== params[idParamName]) {
          console.debug(`🔄 Resource ${resourceType} ID mismatch: ${currentResource._id} vs ${params[idParamName]}`)
          return true
        }

        // 2. Check if any parent resource's ID has changed (e.g., workspace_id)
        // Most resources depend on workspace_id, so if it changes, we should re-fetch.
        if (resourceType !== 'workspace' && params.workspace_id && currentResources['workspace']?._id && currentResources['workspace']._id !== params.workspace_id) {
          console.debug(`🔄 Resource ${resourceType} stale due to workspace change`)
          return true
        }

        return false
      })

      if (resourcesToFetch.length === 0) {
        console.debug('✅ All required resources already loaded')
        setState({
          resources: currentResources,
          loading: currentLoading,
          errors: currentErrors
        })
        return
      }

      console.debug('🔄 Resources to fetch:', resourcesToFetch)

      // Set loading state and clear stale data for resources we're about to fetch
      resourcesToFetch.forEach(resourceType => {
        delete currentResources[resourceType] // Clear stale data to trigger loading state
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
            console.debug(`🚨 Loading ${type}`, params)
            const response = await RESOURCE_LOADERS[type](params)

            // Use the appropriate data extractor for this resource type
            const dataExtractor = RESOURCE_DATA_EXTRACTORS[type]
            if (!dataExtractor)
              throw new Error(`No data extractor defined for resource type: ${type}`)

            const data = dataExtractor(response)
            console.debug(`✅ Loaded ${type}`, data)
            return { type, data, success: true }
          } catch (error) {
            console.error(`❌ Error loading ${type}:`, error)
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
  }, [JSON.stringify(params), JSON.stringify(additionalResources)])

  const value = {
    ...state,
    requestAdditionalResources,
    setResource,
    updateResourceInCollection,
    addResourceToCollection,
    removeResourceFromCollection,

    // Dynamic accessors
    isLoading: (type) => state.loading[type] || false,
    hasError: (type) => !!state.errors[type],
    getError: (type) => state.errors[type] || null,

    // Resource combination helpers
    hasResources: (resourceTypes) => {
      return resourceTypes.every(type => state.resources[type])
    },
    getResources: (resourceTypes) => {
      return resourceTypes.map(type => state.resources[type]).filter(Boolean)
    },

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
  if (!context)
    throw new Error('useResources must be used within a ResourceProvider')
  return context
}

export const useAdditionalResources = (resources) => {
  const { requestAdditionalResources } = useResources()
  useEffect(() => {
    if (resources && resources.length > 0)
      requestAdditionalResources(resources)
  }, [JSON.stringify(resources), requestAdditionalResources])
}

// Convenience hook that just returns the resources object
export const usePageResources = () => {
  const { resources } = useResources()
  return resources
}