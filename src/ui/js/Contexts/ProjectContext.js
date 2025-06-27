import { createContext, useCallback, useContext, useEffect, useState } from 'react'
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
  const [benchmarks, setBenchmarks] = useState({})
  const [benchmarksAggs, setBenchmarksAggs] = useState({})
  const [evaluations, setEvaluations] = useState({})

  // Loading indicators when getting lists of assets
  const [isLoadingProject, setIsLoadingProject] = useState(false)
  const [isLoadingAssets, setIsLoadingAssets] = useState(false)
  const [isLoadingIndices, setIsLoadingIndices] = useState(false)
  const [isLoadingDisplays, setIsLoadingDisplays] = useState(false)
  const [isLoadingScenarios, setIsLoadingScenarios] = useState(false)
  const [isLoadingStrategies, setIsLoadingStrategies] = useState(false)
  const [isLoadingBenchmarks, setIsLoadingBenchmarks] = useState(false)
  const [isLoadingEvaluations, setIsLoadingEvaluations] = useState(false)

  // Loading indicators when getting a single asset
  const [isLoadingDisplay, setIsLoadingDisplay] = useState(false)
  const [isLoadingScenario, setIsLoadingScenario] = useState(false)
  const [isLoadingStrategy, setIsLoadingStrategy] = useState(false)
  const [isLoadingBenchmark, setIsLoadingBenchmark] = useState(false)
  const [isLoadingEvaluation, setIsLoadingEvaluation] = useState(false)

  // Loading indicators when creating, updating, or deleting a single asset
  const [isProcessingDisplay, setIsProcessingDisplay] = useState(false)
  const [isProcessingScenario, setIsProcessingScenario] = useState(false)
  const [isProcessingStrategy, setIsProcessingStrategy] = useState(false)
  const [isProcessingBenchmark, setIsProcessingBenchmark] = useState(false)
  const [isProcessingEvaluation, setIsProcessingEvaluation] = useState(false)

  // High-level loading indicators
  const isLoading = isLoadingProject ||
    isLoadingAssets ||
    isLoadingIndices ||
    isLoadingDisplays || isLoadingDisplay ||
    isLoadingScenarios || isLoadingScenario ||
    isLoadingStrategies || isLoadingStrategy ||
    isLoadingBenchmarks || isLoadingBenchmark ||
    isLoadingEvaluations || isLoadingEvaluation
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
      const response = await api.projects_get(projectId)

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
      strategies,
      benchmarks,
      benchmarksAggs,
      evaluations,
    })
  }, [project, indices, displays, scenarios, strategies, benchmarks, evaluations])

  /**
   * Load project assets when project._id is available, which mean we've
   * navigated to a URL starting with /projects/:project_id and the project
   * was successfully loaded.
   */
  const loadAssets = useCallback(async ({
    indices: shouldLoadIndices,
    displays: shouldLoadDisplays,
    scenarios: shouldLoadScenarios,
    strategies: shouldLoadStrategies,
    benchmarks: shouldLoadBenchmarks,
    evaluations: shouldLoadEvaluations,
  }) => {
    if (!project?._id)
      return
    setIsLoadingAssets(true)
    try {
      const tasks = []

      // Load indices
      if (shouldLoadIndices === true) {
        console.debug(`Loading indices for project: ${projectId}`)
        setIsLoadingIndices(true)
        tasks.push(api.content_mappings_browse(project.index_pattern)
          .then(response => {

            // Set indices
            setIndices(response.data)
          })
          .finally(() => setIsLoadingIndices(false)))
      }

      // Load displays
      if (shouldLoadDisplays === true) {
        console.debug(`Loading displays for project: ${projectId}`)
        setIsLoadingDisplays(true)
        tasks.push(api.displays_browse(projectId)
          .then(response => {

            // Set display docs
            setDisplays(utils.toMap(utils.hitsToDocs(response)))
          })
          .finally(() => setIsLoadingDisplays(false)))
      }

      // Load scenarios
      if (shouldLoadScenarios === true) {
        console.debug(`Loading scenarios for project: ${projectId}`)
        setIsLoadingScenarios(true)
        tasks.push(api.scenarios_browse(projectId)
          .then(response => {

            // Set scenario docs
            setScenarios(utils.toMap(utils.hitsToDocs(response)))

            // Set scenario aggs
            const aggs = {}
            if (response.data.aggregations?.counts?.buckets) {
              response.data.aggregations.counts.buckets.forEach(agg => {
                aggs[agg.key] = {
                  ...aggs[agg.key] || {},
                  judgements: agg.judgements?.doc_count || 0,
                  //evaluations: agg.evaluations?.doc_count || 0
                }
              })
            }
            setScenariosAggs(aggs)
          })
          .finally(() => setIsLoadingScenarios(false)))
      }

      // Load strategies
      if (shouldLoadStrategies === true) {
        console.debug(`Loading strategies for project: ${projectId}`)
        setIsLoadingStrategies(true)
        tasks.push(api.strategies_browse(projectId)
          .then(response => {

            // Set strategy docs
            setStrategies(utils.toMap(utils.hitsToDocs(response)))
          })
          .finally(() => setIsLoadingStrategies(false)))
      }

      // Load benchmarks
      if (shouldLoadBenchmarks) {
        if (shouldLoadBenchmarks === true) {

          // Load all benchmarks
          console.debug(`Loading benchmarks for project: ${projectId}`)
          setIsLoadingBenchmarks(true)
          tasks.push(api.benchmarks_browse(projectId)
            .then(response => {

              // Set benchmark docs
              setBenchmarks(utils.toMap(utils.hitsToDocs(response)))

              // Set benchmark aggs
              const aggs = {}
              if (response.data.aggregations?.counts?.buckets) {
                response.data.aggregations.counts.buckets.forEach(agg => {
                  aggs[agg.key] = {
                    ...aggs[agg.key] || {},
                    benchmarks: agg.benchmarks?.doc_count || 0
                  }
                })
              }
              setBenchmarksAggs(aggs)
            })
            .finally(() => setIsLoadingBenchmarks(false)))

        } else {

          // Load one benchmark
          const benchmarkId = shouldLoadBenchmarks
          console.debug(`Loading benchmark ${benchmarkId} for project: ${projectId}`)
          setIsLoadingBenchmark(true)
          tasks.push(api.benchmarks_get(projectId, benchmarkId)
            .then(response => {

              // Set benchmark docs
              setBenchmarks(utils.toMap(utils.hitsToDocs(response)))
            })
            .finally(() => setIsLoadingBenchmark(false)))

        }
      }

      // Load evaluations
      if (shouldLoadEvaluations) {
        const benchmarkId = shouldLoadEvaluations
        console.debug(`Loading evaluations for project: ${projectId} and benchmark: ${benchmarkId}`)
        setIsLoadingEvaluations(true)
        tasks.push(api.evaluations_browse(projectId, benchmarkId)
          .then(response => {

            // Set evaluation docs
            setEvaluations(utils.toMap(utils.hitsToDocs(response)))
          })
          .finally(() => setIsLoadingEvaluations(false)))
      }

      // Load all requested assets
      await Promise.all(tasks)
    } finally {
      setIsLoadingAssets(false)
    }
  }, [project?._id])

  ////  Mutators  //////////////////////////////////////////////////////////////

  const fnCreate = {
    display: api.displays_create,
    scenario: api.scenarios_create,
    strategy: api.strategies_create,
    benchmark: api.benchmarks_create,
    evaluation: api.evaluations_create,
  }
  const fnUpdate = {
    display: api.displays_update,
    scenario: api.scenarios_update,
    strategy: api.strategies_update,
    benchmark: api.benchmarks_update,
    //evaluation: api.evaluations_update, // evaluations are immutable
  }
  const fnDelete = {
    display: api.displays_delete,
    scenario: api.scenarios_delete,
    strategy: api.strategies_delete,
    benchmark: api.benchmarks_delete,
    evaluation: api.evaluations_delete,
  }
  const fnSetIsProcessing = {
    display: setIsProcessingDisplay,
    scenario: setIsProcessingScenario,
    strategy: setIsProcessingStrategy,
    benchmark: setIsProcessingBenchmark,
    evaluation: setIsProcessingEvaluation,
  }
  const fnSetContext = {
    display: setDisplays,
    scenario: setScenarios,
    strategy: setStrategies,
    benchmark: setBenchmarks,
    evaluation: setEvaluations,
  }

  /**
   * Create, update, or delete a doc
   */
  const handleDoc = async (action, docType, _id, doc) => {
    if (action == 'create')
      console.debug(`Creating ${docType} for project: ${projectId}`)
    else if (action == 'update')
      console.debug(`Updating ${docType} for project: ${projectId}`)
    else if (action == 'delete')
      console.debug(`Deleting ${docType} for project: ${projectId}`)
    let response
    try {
      fnSetIsProcessing[docType](true)
      if (action == 'create')
        response = await fnCreate[docType](projectId, doc)
      else if (action == 'update')
        response = await fnUpdate[docType](projectId, _id, doc)
      else if (action == 'delete')
        response = await fnDelete[docType](projectId, _id)
    } catch (err) {
      return addToast(api.errorToast(err, { title: `Failed to ${action} ${docType}` }))
    } finally {
      fnSetIsProcessing[docType](false)
    }

    // Handle API response
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    addToast(utils.toastDocCreateUpdateDelete(action, docType, _id || response.data._id))
    const newDoc = { ...doc }
    if (action == 'create') {
      // Add doc to context state
      newDoc._id = response.data._id
      fnSetContext[docType](prev => ({ ...prev, [newDoc._id]: newDoc }))
    } else if (action == 'update') {
      // Apply updated fields to doc in context state
      fnSetContext[docType](prev => ({
        ...prev,
        [_id]: Object.fromEntries(
          Object.entries({ ...prev[_id], ...newDoc }).filter(([k, v]) => v !== undefined)
        )
      }))
    } else if (action == 'delete') {
      // Remove doc from context state
      fnSetContext[docType](prev => {
        const copy = { ...prev }
        delete copy[_id]
        return copy
      })
    }

    // Return API response
    return response
  }

  const createDisplay = async (doc) => handleDoc('create', 'display', null, doc)
  const updateDisplay = async (_id, doc) => handleDoc('update', 'display', _id, doc)
  const deleteDisplay = async (_id) => handleDoc('delete', 'display', _id, null)

  const createScenario = async (doc) => handleDoc('create', 'scenario', null, doc)
  const updateScenario = async (_id, doc) => handleDoc('update', 'scenario', _id, doc)
  const deleteScenario = async (_id) => handleDoc('delete', 'scenario', _id, null)

  const createStrategy = async (doc) => handleDoc('create', 'strategy', null, doc)
  const updateStrategy = async (_id, doc) => handleDoc('update', 'strategy', _id, doc)
  const deleteStrategy = async (_id) => handleDoc('delete', 'strategy', _id, null)

  const createBenchmark = async (doc) => handleDoc('create', 'benchmark', null, doc)
  const updateBenchmark = async (_id, doc) => handleDoc('update', 'benchmark', _id, doc)
  const deleteBenchmark = async (_id) => handleDoc('delete', 'benchmark', _id, null)

  const createEvaluation = async (doc) => handleDoc('create', 'evaluation', null, doc)
  //const updateEvaluation = async (_id, doc) => handleDoc('update', 'evaluation', _id, doc) // evaluations are immutable
  const deleteEvaluation = async (_id) => handleDoc('delete', 'evaluation', _id, null)

  return (
    <ProjectContext.Provider value={{

      // Project and assets
      project,
      indices,
      displays,
      scenarios, scenariosAggs,
      strategies,
      benchmarks, benchmarksAggs,
      evaluations,

      // Loaders
      loadProject, loadAssets,

      // Loading indicators
      isLoading,
      isLoadingProject,
      isLoadingIndices,
      isLoadingDisplays, isLoadingDisplay, isProcessingDisplay,
      isLoadingScenarios, isLoadingScenario, isProcessingScenario,
      isLoadingStrategies, isLoadingStrategy, isProcessingStrategy,
      isLoadingBenchmarks, isLoadingBenchmark, isProcessingBenchmark,
      isLoadingEvaluations, isLoadingEvaluation, isProcessingEvaluation,
      isProjectReady,

      // Mutators
      createDisplay, updateDisplay, deleteDisplay,
      createScenario, updateScenario, deleteScenario,
      createStrategy, updateStrategy, deleteStrategy,
      createBenchmark, updateBenchmark, deleteBenchmark,
      createEvaluation, deleteEvaluation,
    }}>
      {children}
    </ProjectContext.Provider>
  )
}