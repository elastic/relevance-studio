/**
 * api.js
 * 
 * Implements API requests implemented by the esrs server.
 */

import { EuiText } from '@elastic/eui'
import { getAppContext } from './Contexts/AppContext'
import client from './client'
import { SetupIncompleteError } from './errors'
import { getHistory } from './history'

const api = {}

/**
 * Template for toasts for error messages.
 */
api.errorToast = (e, props) => {
  console.error(e)
  return {
    title: props?.title || e.response?.statusText || e.statusText,
    color: props?.color || 'danger',
    text: (
      <EuiText size='xs' color='subdued'>
        {props?.text || e.error?.reason || e.message || JSON.stringify(e, null, 2)}
      </EuiText>
    )
  }
}

const validateArgs = (fnName, requiredArgs) => {
  for (const [arg, value] of Object.entries(requiredArgs)) {
    if (value === undefined)
      throw new Error(`${fnName} requires ${arg}`)
  }
}

/**
 * Remove fields from a doc that shouldn't be included in creates or updates.
 */
const clean = (doc) => {
  const sanitized = { ...doc }
  delete sanitized['_id']
  delete sanitized['@meta']
  return sanitized
}

/**
 * Return a response, or redirect to home if the status is 404,
 * indicating that the index templates and indices aren't setup.
 */
const responseOrFallbackSetup = (response) => {
  if (response?.status === 404 && response?.data?.error?.index?.startsWith('esrs-')) {
    const ctx = getAppContext()
    ctx?.setIsSetup?.(false)
    getHistory().push('/')
    throw new SetupIncompleteError()
  }
  return response
}

////  API: Projects  ///////////////////////////////////////////////////////////

api.projects_search = async (body) => {
  const response = await client.post(`/api/projects/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.projects_get = async (project_id) => {
  validateArgs('api.projects_get', { project_id, })
  const response = await client.get(`/api/projects/${project_id}`)
  return responseOrFallbackSetup(response)
}

api.projects_create = async (doc) => {
  validateArgs('api.projects_create', { doc, })
  const response = await client.post(`/api/projects`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.projects_update = async (project_id, doc_partial) => {
  validateArgs('api.projects_update', { project_id, doc_partial, })
  const response = await client.put(`/api/projects/${project_id}`, { data: clean(doc_partial) })
  return responseOrFallbackSetup(response)
}

api.projects_delete = async (project_id) => {
  validateArgs('api.projects_delete', { project_id, })
  const response = await client.del(`/api/projects/${project_id}`)
  return responseOrFallbackSetup(response)
}


////  API: Displays  ///////////////////////////////////////////////////////////

api.displays_search = async (project_id, body) => {
  validateArgs('api.displays_search', { project_id, })
  const response = await client.post(`/api/projects/${project_id}/displays/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.displays_get = async (project_id, display_id) => {
  validateArgs('api.displays_get', { project_id, display_id, })
  const response = await client.get(`/api/projects/${project_id}/displays/${display_id}`)
  return responseOrFallbackSetup(response)
}

api.displays_create = async (project_id, doc) => {
  validateArgs('api.displays_create', { project_id, doc, })
  const response = await client.post(`/api/projects/${project_id}/displays`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.displays_update = async (project_id, display_id, doc_partial) => {
  validateArgs('api.displays_update', { project_id, display_id, doc_partial, })
  const response = await client.put(`/api/projects/${project_id}/displays/${display_id}`, { data: clean(doc_partial) })
  return responseOrFallbackSetup(response)
}

api.displays_delete = async (project_id, display_id) => {
  validateArgs('api.displays_delete', { project_id, display_id, })
  const response = await client.del(`/api/projects/${project_id}/displays/${display_id}`)
  return responseOrFallbackSetup(response)
}


////  API: Scenarios  //////////////////////////////////////////////////////////

api.scenarios_search = async (project_id, body) => {
  validateArgs('api.scenarios_search', { project_id, })
  const response = await client.post(`/api/projects/${project_id}/scenarios/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.scenarios_tags = async (project_id) => {
  validateArgs('api.scenarios_tags', { project_id, })
  const response = await client.get(`/api/projects/${project_id}/scenarios/_tags`)
  return responseOrFallbackSetup(response)
}

api.scenarios_get = async (project_id, scenario_id) => {
  validateArgs('api.scenarios_get', { project_id, scenario_id, })
  const response = await client.get(`/api/projects/${project_id}/scenarios/${scenario_id}`)
  return responseOrFallbackSetup(response)
}

api.scenarios_create = async (project_id, doc) => {
  validateArgs('api.scenarios_create', { project_id, doc, })
  const response = await client.post(`/api/projects/${project_id}/scenarios`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.scenarios_update = async (project_id, scenario_id, doc_partial) => {
  validateArgs('api.scenarios_update', { project_id, scenario_id, doc_partial, })
  const response = await client.put(`/api/projects/${project_id}/scenarios/${scenario_id}`, { data: clean(doc_partial) })
  return responseOrFallbackSetup(response)
}

api.scenarios_delete = async (project_id, scenario_id) => {
  validateArgs('api.scenarios_delete', { project_id, scenario_id, })
  const response = await client.del(`/api/projects/${project_id}/scenarios/${scenario_id}`)
  return responseOrFallbackSetup(response)
}


////  API: Judgements  /////////////////////////////////////////////////////////

api.judgements_search = async (project_id, scenario_id, body, params) => {
  validateArgs('api.judgements_search', { project_id, scenario_id, body, })
  body.project_id = project_id
  body.scenario_id = scenario_id
  const response = await client.post(`/api/projects/${project_id}/judgements/_search`, { data: body, params: params })
  return responseOrFallbackSetup(response)
}

api.judgements_set = async (project_id, scenario_id, doc) => {
  validateArgs('api.judgements_set', { project_id, scenario_id, doc, })
  doc.project_id = project_id
  doc.scenario_id = scenario_id
  const response = await client.put(`/api/projects/${project_id}/judgements`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.judgements_unset = async (project_id, judgement_id) => {
  validateArgs('api.judgements_unset', { project_id, judgement_id, })
  const response = await client.del(`/api/projects/${project_id}/judgements/${judgement_id}`)
  return responseOrFallbackSetup(response)
}


////  API: Strategies  /////////////////////////////////////////////////////////

api.strategies_search = async (project_id, body) => {
  validateArgs('api.strategies_search', { project_id, })
  const response = await client.post(`/api/projects/${project_id}/strategies/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.strategies_tags = async (project_id) => {
  validateArgs('api.strategies_tags', { project_id, })
  const response = await client.get(`/api/projects/${project_id}/strategies/_tags`)
  return responseOrFallbackSetup(response)
}

api.strategies_get = async (project_id, strategy_id) => {
  validateArgs('api.strategies_get', { project_id, strategy_id, })
  const response = await client.get(`/api/projects/${project_id}/strategies/${strategy_id}`)
  return responseOrFallbackSetup(response)
}

api.strategies_create = async (project_id, doc) => {
  validateArgs('api.strategies_create', { project_id, doc, })
  const response = await client.post(`/api/projects/${project_id}/strategies`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.strategies_update = async (project_id, strategy_id, doc_partial) => {
  validateArgs('api.strategies_update', { project_id, strategy_id, doc_partial, })
  const response = await client.put(`/api/projects/${project_id}/strategies/${strategy_id}`, { data: clean(doc_partial) })
  return responseOrFallbackSetup(response)
}

api.strategies_delete = async (project_id, strategy_id) => {
  validateArgs('api.strategyies_delete', { project_id, strategy_id, })
  const response = await client.del(`/api/projects/${project_id}/strategies/${strategy_id}`)
  return responseOrFallbackSetup(response)
}


////  API: Benchmarks  /////////////////////////////////////////////////////////

api.benchmarks_search = async (project_id, body) => {
  validateArgs('api.benchmarks_search', { project_id, })
  const response = await client.post(`/api/projects/${project_id}/benchmarks/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.benchmarks_tags = async (project_id) => {
  validateArgs('api.benchmarks_tags', { project_id, })
  const response = await client.get(`/api/projects/${project_id}/benchmarks/_tags`)
  return responseOrFallbackSetup(response)
}

api.benchmarks_get = async (project_id, benchmark_id) => {
  validateArgs('api.benchmarks_get', { project_id, benchmark_id, })
  const response = await client.get(`/api/projects/${project_id}/benchmarks/${benchmark_id}`)
  return responseOrFallbackSetup(response)
}

api.benchmarks_create = async (project_id, doc) => {
  validateArgs('api.benchmarks_create', { project_id, doc, })
  const response = await client.post(`/api/projects/${project_id}/benchmarks`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.benchmarks_update = async (project_id, benchmark_id, doc_partial) => {
  validateArgs('api.benchmarks_update', { project_id, benchmark_id, doc_partial, })
  const response = await client.put(`/api/projects/${project_id}/benchmarks/${benchmark_id}`, { data: clean(doc_partial) })
  return responseOrFallbackSetup(response)
}

api.benchmarks_delete = async (project_id, benchmark_id) => {
  validateArgs('api.benchmarks_delete', { project_id, benchmark_id, })
  const response = await client.del(`/api/projects/${project_id}/benchmarks/${benchmark_id}`)
  return responseOrFallbackSetup(response)
}

api.benchmarks_make_candidate_pool = async (project_id, body) => {
  validateArgs('api.benchmarks_make_candidate_pool', { project_id, body })
  const response = await client.post(`/api/projects/${project_id}/benchmarks/_candidates`, { data: body })
  return responseOrFallbackSetup(response)
}


////  API: Evaluations  ////////////////////////////////////////////////////////

api.evaluations_search = async (project_id, benchmark_id, body) => {
  validateArgs('api.evaluations_search', { project_id, benchmark_id, })
  const response = await client.post(`/api/projects/${project_id}/benchmarks/${benchmark_id}/evaluations/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.evaluations_get = async (project_id, benchmark_id, evaluation_id) => {
  validateArgs('api.evaluations_get', { project_id, benchmark_id, evaluation_id, })
  const response = await client.get(`/api/projects/${project_id}/benchmarks/${benchmark_id}/evaluations/${evaluation_id}`)
  return responseOrFallbackSetup(response)
}

api.evaluations_create = async (project_id, benchmark_id, body) => {
  validateArgs('api.evaluations_create', { project_id, benchmark_id, body, })
  const response = await client.post(`/api/projects/${project_id}/benchmarks/${benchmark_id}/evaluations`, { data: clean(body) })
  return responseOrFallbackSetup(response)
}

api.evaluations_run = async (project_id, body) => {
  validateArgs('api.evaluations_run', { project_id, body, })
  const response = await client.post(`/api/projects/${project_id}/evaluations/_run`, { data: body })
  return responseOrFallbackSetup(response)
}

api.evaluations_delete = async (project_id, benchmark_id, evaluation_id) => {
  validateArgs('api.evaluations_delete', { project_id, benchmark_id, evaluation_id, })
  const response = await client.del(`/api/projects/${project_id}/benchmarks/${benchmark_id}/evaluations/${evaluation_id}`)
  return responseOrFallbackSetup(response)
}


////  API: Indices  ////////////////////////////////////////////////////////////

api.content_search = async (index_pattern, body, params) => {
  validateArgs('api.content_search', { index_pattern, body, })
  return await client.post(`/api/content/_search/${index_pattern}`, { data: body, param: params })
}

api.content_mappings_browse = async (index_pattern) => {
  validateArgs('api.content_mappings_browse', { index_pattern, })
  return await client.get(`/api/content/mappings/${index_pattern}`)
}


////  API: Setup  //////////////////////////////////////////////////////////////

api.setup_check = async () => {
  return await client.get(`/api/setup`)
}

api.setup_run = async () => {
  return await client.post(`/api/setup`)
}

export default api