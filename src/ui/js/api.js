/**
 * api.js
 * 
 * Implements API requests implemented by the esrs server.
 */

import { EuiText } from '@elastic/eui'
import client from './client'

const api = {}

/**
 * Template for toasts for error messages.
 */
api.errorToast = (err, props) => {
  console.error(err)
  return {
    title: props?.title || err.response?.statusText || err.statusText,
    color: props?.color || 'danger',
    text: (
      <EuiText size='xs' color='subdued'>
        {props?.text || err.message || JSON.stringify(err, null, 2)}
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

////  API: Projects  ///////////////////////////////////////////////////////////

api.projects_search = async (body) => {
  return await client.post(`/api/projects/_search`, body ? { data: body } : {})
}

api.projects_tags = async () => {
  return await client.get(`/api/projects/_tags`)
}

api.projects_get = async (project_id) => {
  validateArgs('api.projects_get', { project_id, })
  return await client.get(`/api/projects/${project_id}`)
}

api.projects_create = async (doc) => {
  validateArgs('api.projects_create', { doc, })
  return await client.post(`/api/projects`, { data: doc })
}

api.projects_update = async (project_id, doc) => {
  validateArgs('api.projects_update', { project_id, doc, })
  return await client.put(`/api/projects/${project_id}`, { data: doc })
}

api.projects_delete = async (project_id) => {
  validateArgs('api.projects_delete', { project_id, })
  return await client.del(`/api/projects/${project_id}`)
}


////  API: Displays  ///////////////////////////////////////////////////////////

api.displays_search = async (project_id, body) => {
  validateArgs('api.displays_search', { project_id, })
  return await client.post(`/api/projects/${project_id}/displays/_search`, body ? { data: body } : {})
}

api.displays_get = async (project_id, display_id) => {
  validateArgs('api.displays_get', { project_id, display_id, })
  return await client.get(`/api/projects/${project_id}/displays/${display_id}`)
}

api.displays_create = async (project_id, doc) => {
  validateArgs('api.displays_create', { project_id, doc, })
  return await client.post(`/api/projects/${project_id}/displays`, { data: doc })
}

api.displays_update = async (project_id, display_id, doc) => {
  validateArgs('api.displays_update', { project_id, display_id, doc, })
  return await client.put(`/api/projects/${project_id}/displays/${display_id}`, { data: doc })
}

api.displays_delete = async (project_id, display_id) => {
  validateArgs('api.displays_delete', { project_id, display_id, })
  return await client.del(`/api/projects/${project_id}/displays/${display_id}`)
}


////  API: Scenarios  //////////////////////////////////////////////////////////

api.scenarios_search = async (project_id, body) => {
  validateArgs('api.scenarios_search', { project_id, })
  return await client.post(`/api/projects/${project_id}/scenarios/_search`, body ? { data: body } : {})
}

api.scenarios_tags = async (project_id) => {
  validateArgs('api.scenarios_tags', { project_id, })
  return await client.get(`/api/projects/${project_id}/scenarios/_tags`)
}

api.scenarios_get = async (project_id, scenario_id) => {
  validateArgs('api.scenarios_get', { project_id, scenario_id, })
  return await client.get(`/api/projects/${project_id}/scenarios/${scenario_id}`)
}

api.scenarios_create = async (project_id, doc) => {
  validateArgs('api.scenarios_create', { project_id, doc, })
  return await client.post(`/api/projects/${project_id}/scenarios`, { data: doc })
}

api.scenarios_update = async (project_id, scenario_id, doc) => {
  validateArgs('api.scenarios_update', { project_id, scenario_id, doc, })
  return await client.put(`/api/projects/${project_id}/scenarios/${scenario_id}`, { data: doc })
}

api.scenarios_delete = async (project_id, scenario_id) => {
  validateArgs('api.scenarios_delete', { project_id, scenario_id, })
  return await client.del(`/api/projects/${project_id}/scenarios/${scenario_id}`)
}


////  API: Judgements  /////////////////////////////////////////////////////////

api.judgements_search = async (project_id, scenario_id, body, params) => {
  validateArgs('api.judgements_search', { project_id, scenario_id, body, })
  body.project_id = project_id
  body.scenario_id = scenario_id
  return await client.post(`/api/projects/${project_id}/judgements/_search`, { data: body, params: params })
}

api.judgements_set = async (project_id, scenario_id, doc) => {
  validateArgs('api.judgements_set', { project_id, scenario_id, doc, })
  doc.project_id = project_id
  doc.scenario_id = scenario_id
  return await client.put(`/api/projects/${project_id}/judgements`, { data: doc })
}

api.judgements_unset = async (project_id, judgement_id) => {
  validateArgs('api.judgements_unset', { project_id, judgement_id, })
  return await client.del(`/api/projects/${project_id}/judgements/${judgement_id}`)
}


////  API: Strategies  /////////////////////////////////////////////////////////

api.strategies_search = async (project_id, body) => {
  validateArgs('api.strategies_search', { project_id, })
  return await client.post(`/api/projects/${project_id}/strategies/_search`, body ? { data: body } : {})
}

api.strategies_tags = async (project_id) => {
  validateArgs('api.strategies_tags', { project_id, })
  return await client.get(`/api/projects/${project_id}/strategies/_tags`)
}

api.strategies_get = async (project_id, strategy_id) => {
  validateArgs('api.strategies_get', { project_id, strategy_id, })
  return await client.get(`/api/projects/${project_id}/strategies/${strategy_id}`)
}

api.strategies_create = async (project_id, doc) => {
  validateArgs('api.strategies_create', { project_id, doc, })
  return await client.post(`/api/projects/${project_id}/strategies`, { data: doc })
}

api.strategies_update = async (project_id, strategy_id, doc) => {
  validateArgs('api.strategies_update', { project_id, strategy_id, doc, })
  return await client.put(`/api/projects/${project_id}/strategies/${strategy_id}`, { data: doc })
}

api.strategies_delete = async (project_id, strategy_id) => {
  validateArgs('api.strategyies_delete', { project_id, strategy_id, })
  return await client.del(`/api/projects/${project_id}/strategies/${strategy_id}`)
}


////  API: Benchmarks  /////////////////////////////////////////////////////////

api.benchmarks_search = async (project_id, body) => {
  validateArgs('api.benchmarks_search', { project_id, })
  return await client.post(`/api/projects/${project_id}/benchmarks/_search`, body ? { data: body } : {})
}

api.benchmarks_tags = async (project_id) => {
  validateArgs('api.benchmarks_tags', { project_id, })
  return await client.get(`/api/projects/${project_id}/benchmarks/_tags`)
}

api.benchmarks_get = async (project_id, benchmark_id) => {
  validateArgs('api.benchmarks_get', { project_id, benchmark_id, })
  return await client.get(`/api/projects/${project_id}/benchmarks/${benchmark_id}`)
}

api.benchmarks_create = async (project_id, doc) => {
  validateArgs('api.benchmarks_create', { project_id, doc, })
  return await client.post(`/api/projects/${project_id}/benchmarks`, { data: doc })
}

api.benchmarks_update = async (project_id, benchmark_id, doc) => {
  validateArgs('api.benchmarks_update', { project_id, benchmark_id, doc, })
  return await client.put(`/api/projects/${project_id}/benchmarks/${benchmark_id}`, { data: doc })
}

api.benchmarks_delete = async (project_id, benchmark_id) => {
  validateArgs('api.benchmarks_delete', { project_id, benchmark_id, })
  return await client.del(`/api/projects/${project_id}/benchmarks/${benchmark_id}`)
}

api.benchmarks_make_candidate_pool = async (project_id, body) => {
  validateArgs('api.benchmarks_make_candidate_pool', { project_id, body })
  return await client.post(`/api/projects/${project_id}/benchmarks/_candidates`, { data: body })
}


////  API: Evaluations  ////////////////////////////////////////////////////////

api.evaluations_search = async (project_id, benchmark_id, body) => {
  validateArgs('api.evaluations_search', { project_id, benchmark_id, })
  return await client.post(`/api/projects/${project_id}/benchmarks/${benchmark_id}/evaluations/_search`, body ? { data: body } : {})
}

api.evaluations_get = async (project_id, benchmark_id, evaluation_id) => {
  validateArgs('api.evaluations_get', { project_id, benchmark_id, evaluation_id, })
  return await client.get(`/api/projects/${project_id}/benchmarks/${benchmark_id}/evaluations/${evaluation_id}`)
}

api.evaluations_create = async (project_id, benchmark_id, doc) => {
  validateArgs('api.evaluations_create', { project_id, benchmark_id, doc, })
  return await client.post(`/api/projects/${project_id}/benchmarks/${benchmark_id}/evaluations`, { data: doc })
}

api.evaluations_delete = async (project_id, benchmark_id, evaluation_id) => {
  validateArgs('api.evaluations_delete', { project_id, benchmark_id, evaluation_id, })
  return await client.del(`/api/projects/${project_id}/benchmarks/${benchmark_id}/evaluations/${evaluation_id}`)
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

api.setup = async () => {
  return await client.post(`/api/setup`)
}

export default api