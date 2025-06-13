import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState
} from 'react'
import { useParams } from 'react-router-dom'
import { useAppContext } from './AppContext'
import api from '../api'
import utils from '../utils'

export const ProjectContext = createContext()
export const useProjectContext = () => useContext(ProjectContext)

export const ProjectProvider = ({ children }) => {

  /**
   * projectId comes from the URL path: /projects/:project_id
   */
  const { project_id: projectId } = useParams()

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  // Project assets
  const [project, setProject] = useState(null)
  const [indices, setIndices] = useState({})
  const [displays, setDisplays] = useState({})
  const [scenarios, setScenarios] = useState({})
  const [scenariosAggs, setScenariosAggs] = useState({})
  const [strategies, setStrategies] = useState({})

  // Loading indicators when getting lists of assets
  const [isLoadingProject, setIsLoadingProject] = useState(false)
  const [isLoadingIndices, setIsLoadingIndices] = useState(false)
  const [isLoadingDisplays, setIsLoadingDisplays] = useState(false)
  const [isLoadingScenarios, setIsLoadingScenarios] = useState(false)
  const [isLoadingStrategies, setIsLoadingStrategies] = useState(false)

  // Loading indicators when getting a single asset
  const [isLoadingDisplay, setIsLoadingDisplay] = useState(false)
  const [isLoadingScenario, setIsLoadingScenario] = useState(false)
  const [isLoadingStrategy, setIsLoadingStrategy] = useState(false)

  // Loading indicators when creating, updating, or deleting a single asset
  const [isProcessingDisplay, setIsProcessingDisplay] = useState(false)
  const [isProcessingScenario, setIsProcessingScenario] = useState(false)
  const [isProcessingStrategy, setIsProcessingStrategy] = useState(false)

  // High-level loading indicators
  const isLoading = isLoadingProject || isLoadingIndices || isLoadingDisplays || isLoadingScenarios || isLoadingStrategies
  const isProjectReady = project && !isLoading

  ////  Loaders  ///////////////////////////////////////////////////////////////

  /**
   * Load project when projectId changes, which happens when we navigate
   * to a URL starting with /projects/:project_id
   */
  const loadProject = useCallback(async () => {
    console.debug(`Loading project: ${projectId}`)
    setIsLoadingProject(true)
    try {
      const response = await api.get_project(projectId)

      // Set project doc
      const _project = response.data._source
      _project._id = response.data._id
      setProject(_project)
    } catch (err) {
      return addToast(api.errorToast(err, {
        title: `Failed to load project: ${projectId}`
      }))
    } finally {
      setIsLoadingProject(false)
    }
  }, [projectId])

  /**
   * Automatically load the project data when the ProjectProvider mounts
   * or when the projectId in the URL changes (e.g. navigating between projects).
   */
  useEffect(() => {
    const run = async () => {
      await loadProject()
    }
    run()
  }, [loadProject])

  /**
   * Log project context state
   */
  useEffect(() => {
    if (!project)
      return
    console.debug('[ProjectContext state updated]', {
      projectId: project._id,
      indices,
      displays,
      scenarios,
      scenariosAggs,
      strategies
    })
  }, [project, indices, displays, scenarios, strategies])

  /**
   * Load project assets when project._id is available, which mean we've
   * navigated to a URL starting with /projects/:project_id and the project
   * was successfully loaded.
   */
  const loadAssets = useCallback(async ({
    indices: shouldLoadIndices,
    displays: shouldLoadDisplays,
    scenarios: shouldLoadScenarios,
    strategies: shouldLoadStrategies
  }) => {
    if (!project?._id)
      return
    const tasks = []

    // Load indices
    if (shouldLoadIndices) {
      console.debug(`Loading indices for project: ${projectId}`)
      setIsLoadingIndices(true)
      tasks.push(api.get_indices(project.index_pattern)
        .then(response => {

          // Set indices
          setIndices(response.data)
        })
        .finally(() => setIsLoadingIndices(false)))
    }

    // Load displays
    if (shouldLoadDisplays) {
      console.debug(`Loading displays for project: ${projectId}`)
      setIsLoadingDisplays(true)
      tasks.push(api.get_displays(projectId)
        .then(response => {

          // Set display docs
          setDisplays(utils.toMap(utils.hitsToDocs(response)))
        })
        .finally(() => setIsLoadingDisplays(false)))
    }

    // Load scenarios
    if (shouldLoadScenarios) {
      console.debug(`Loading scenarios for project: ${projectId}`)
      setIsLoadingScenarios(true)
      tasks.push(api.get_scenarios(projectId)
        .then(response => {

          // Set scenario docs
          setScenarios(utils.toMap(utils.hitsToDocs(response)))

          // Set scenario aggs
          const aggs = {}
          response.data.aggregations.counts?.buckets.forEach(agg => {
            aggs[agg.key] = {
              ...aggs[agg.key] || {},
              judgements: agg.judgements.doc_count,
              //evaluations: agg.evaluations.doc_count
            }
          })
          setScenariosAggs(aggs)
        })
        .finally(() => setIsLoadingScenarios(false)))
    }

    // Load strategies
    if (shouldLoadStrategies) {
      console.debug(`Loading strategies for project: ${projectId}`)
      setIsLoadingStrategies(true)
      tasks.push(api.get_strategies(projectId)
        .then(response => {

          // Set strategy docs
          setStrategies(utils.toMap(utils.hitsToDocs(response)))
        })
        .finally(() => setIsLoadingStrategies(false)))
    }

    await Promise.all(tasks)
  }, [project?._id])

  ////  Mutators  //////////////////////////////////////////////////////////////

  const fnCreate = {
    display: api.create_display,
    scenario: api.create_scenario,
    strategy: api.create_strategy,
  }
  const fnUpdate = {
    display: api.update_display,
    scenario: api.update_scenario,
    strategy: api.update_strategy,
  }
  const fnDelete = {
    display: api.delete_display,
    scenario: api.delete_scenario,
    strategy: api.delete_strategy,
  }
  const fnSetIsProcessing = {
    display: setIsProcessingDisplay,
    scenario: setIsProcessingScenario,
    strategy: setIsProcessingStrategy,
  }
  const fnSetContext = {
    display: setDisplays,
    scenario: setScenarios,
    strategy: setStrategies,
  }

  /**
   * Create, update, or delete a doc
   */
  const handleDoc = async (action, docType, doc) => {
    console.debug(`Creating ${docType} for project: ${projectId}`)
    console.warn(doc)
    let response
    try {
      fnSetIsProcessing[docType](true)
      if (action == 'create')
        response = await fnCreate[docType](projectId, doc)
      else if (action == 'update')
        response = await fnUpdate[docType](projectId, doc._id, doc)
      else if (action == 'delete')
        response = await fnDelete[docType](projectId, doc._id)
    } catch (err) {
      return addToast(api.errorToast(err, { title: `Failed to ${action} ${docType}` }))
    } finally {
      fnSetIsProcessing[docType](false)
    }

    // Handle API response
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    addToast(utils.toastDocCreateUpdateDelete(action, docType, doc))
    const newDoc = { ...doc }
    if (action == 'create') {

      // Add doc to context state
      newDoc._id = response.data._id
      fnSetContext[docType](prev => ({ ...prev, [newDoc._id]: newDoc }))

    } else if (action == 'update') {
      // Add doc to context state
      fnSetContext[docType](prev => ({ ...prev, [newDoc._id]: newDoc }))

    } else if (action == 'delete') {
      // Remove doc from context state
      fnSetContext[docType](prev => {
        const copy = { ...prev }
        delete copy[doc._id]
        return copy
      })
    }

    // Return API response
    return response
  }

  const createDisplay = async (doc) => handleDoc('create', 'display', doc)
  const updateDisplay = async (doc) => handleDoc('update', 'display', doc)
  const deleteDisplay = async (doc) => handleDoc('delete', 'display', doc)

  const createScenario = async (doc) => handleDoc('create', 'scenario', doc)
  const updateScenario = async (doc) => handleDoc('update', 'scenario', doc)
  const deleteScenario = async (doc) => handleDoc('delete', 'scenario', doc)

  const createStrategy = async (doc) => handleDoc('create', 'strategy', doc)
  const updateStrategy = async (doc) => handleDoc('update', 'strategy', doc)
  const deleteStrategy = async (doc) => handleDoc('delete', 'strategy', doc)

  return (
    <ProjectContext.Provider value={{

      // Project and assets
      project, indices, displays, scenarios, scenariosAggs, strategies,

      // Loaders
      loadProject, loadAssets,

      // Loading indicators
      isLoading,
      isLoadingProject,
      isLoadingIndices,
      isLoadingDisplays, isLoadingDisplay, isProcessingDisplay,
      isLoadingScenarios, isLoadingScenario, isProcessingScenario,
      isLoadingStrategies, isLoadingStrategy, isProcessingStrategy,
      isProjectReady,

      // Mutators
      createDisplay, updateDisplay, deleteDisplay,
      createScenario, updateScenario, deleteScenario,
      createStrategy, updateStrategy, deleteStrategy
    }}>
      {children}
    </ProjectContext.Provider>
  )
}