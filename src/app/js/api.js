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

////  Projects  ////////////////////////////////////////////////////////////////

api.get_projects = async () => {
  return await client.get(`/projects`)
}

api.get_project = async (project_id) => {
  validateArgs('api.get_project', { project_id, })
  return await client.get(`/projects/${project_id}`)
}

api.create_project = async (doc) => {
  validateArgs('api.create_project', { doc, })
  return await client.post(`/projects`, { data: doc })
}

api.update_project = async (project_id, doc) => {
  validateArgs('api.update_project', { project_id, doc, })
  return await client.put(`/projects/${project_id}`, { data: doc })
}

api.delete_project = async (project_id) => {
  validateArgs('api.delete_project', { project_id, })
  return await client.del(`/projects/${project_id}`)
}


////  Displays  ////////////////////////////////////////////////////////////////

api.get_displays = async (project_id) => {
  validateArgs('api.get_displays', { project_id, })
  return await client.get(`/projects/${project_id}/displays`)
}

api.get_display = async (project_id, display_id) => {
  validateArgs('api.get_display', { project_id, display_id, })
  return await client.get(`/projects/${project_id}/displays/${display_id}`)
}

api.create_display = async (project_id, doc) => {
  validateArgs('api.create_display', { project_id, doc, })
  return await client.post(`/projects/${project_id}/displays`, { data: doc })
}

api.update_display = async (project_id, display_id, doc) => {
  validateArgs('api.update_display', { project_id, display_id, doc, })
  return await client.put(`/projects/${project_id}/displays/${display_id}`, { data: doc })
}

api.delete_display = async (project_id, display_id) => {
  validateArgs('api.delete_display', { project_id, display_id, })
  return await client.del(`/projects/${project_id}/displays/${display_id}`)
}


////  Scenarios  ///////////////////////////////////////////////////////////////

api.get_scenarios = async (project_id) => {
  validateArgs('api.get_scenarios', { project_id, })
  return await client.get(`/projects/${project_id}/scenarios`)
}

api.get_scenario = async (project_id, scenario_id) => {
  validateArgs('api.get_scenario', { project_id, scenario_id, })
  return await client.get(`/projects/${project_id}/scenarios/${scenario_id}`)
}

api.create_scenario = async (project_id, doc) => {
  validateArgs('api.create_scenario', { project_id, doc, })
  return await client.post(`/projects/${project_id}/scenarios`, { data: doc })
}

api.update_scenario = async (project_id, scenario_id, doc) => {
  validateArgs('api.update_scenario', { project_id, scenario_id, doc, })
  return await client.put(`/projects/${project_id}/scenarios/${scenario_id}`, { data: doc })
}

api.delete_scenario = async (project_id, scenario_id) => {
  validateArgs('api.delete_scenario', { project_id, scenario_id, })
  return await client.del(`/projects/${project_id}/scenarios/${scenario_id}`)
}


////  Judgements  //////////////////////////////////////////////////////////////

api.get_judgements_docs = async (project_id, scenario_id, body, params) => {
  validateArgs('api.get_judgements_docs', { project_id, scenario_id, body, })
  return await client.post(`/projects/${project_id}/scenarios/${scenario_id}/judgements/_docs`, { data: body, params: params })
}

api.get_judgements = async (project_id) => {
  validateArgs('api.get_judgements', { project_id, })
  return await client.get(`/projects/${project_id}/judgements`)
}

api.get_judgement = async (project_id, judgement_id) => {
  validateArgs('api.get_judgement', { project_id, judgement_id, })
  return await client.get(`/projects/${project_id}/judgements/${judgement_id}`)
}

api.set_judgement = async (project_id, scenario_id, doc) => {
  validateArgs('api.set_judgement', { project_id, scenario_id, doc, })
  return await client.put(`/projects/${project_id}/scenarios/${scenario_id}/judgements`, { data: doc })
}

api.unset_judgement = async (project_id, scenario_id, doc) => {
  validateArgs('api.unset_judgement', { project_id, scenario_id, doc, })
  return await client.del(`/projects/${project_id}/scenarios/${scenario_id}/judgements`, { data: doc })
}


////  Strategies  //////////////////////////////////////////////////////////////

api.get_strategies = async (project_id) => {
  validateArgs('api.get_strategies', { project_id, })
  return await client.get(`/projects/${project_id}/strategies`)
}

api.get_strategy = async (project_id, strategy_id) => {
  validateArgs('api.get_strategy', { project_id, strategy_id, })
  return await client.get(`/projects/${project_id}/strategies/${strategy_id}`)
}

api.create_strategy = async (project_id, doc) => {
  validateArgs('api.create_strategy', { project_id, doc, })
  return await client.post(`/projects/${project_id}/strategies`, { data: doc })
}

api.update_strategy = async (project_id, strategy_id, doc) => {
  validateArgs('api.update_strategy', { project_id, strategy_id, doc, })
  return await client.put(`/projects/${project_id}/strategies/${strategy_id}`, { data: doc })
}

api.delete_strategy = async (project_id, strategy_id) => {
  validateArgs('api.delete_strategy', { project_id, strategy_id, })
  return await client.del(`/projects/${project_id}/strategies/${strategy_id}`)
}


////  Evaluations  /////////////////////////////////////////////////////////////

api.get_evaluations = async (project_id) => {
  validateArgs('api.get_evaluations', { project_id, })
  return await client.get(`/projects/${project_id}/evaluations`)
}

api.get_evaluation = async (project_id, evaluation_id) => {
  validateArgs('api.get_evaluation', { project_id, evaluation_id, })
  return await client.get(`/projects/${project_id}/evaluations/${evaluation_id}`)
}

api.run_evaluation = async (project_id, body, params) => {
  validateArgs('api.run_evaluation', { project_id, body, })
  return await client.post(`/projects/${project_id}/evaluations`, { data: body, params: params })
}

api.delete_evaluation = async (project_id, evaluation_id) => {
  validateArgs('api.delete_evaluation', { project_id, evaluation_id, })
  return await client.del(`/projects/${project_id}/evaluations/${evaluation_id}`)
}


////  Other  ///////////////////////////////////////////////////////////////////

api.get_indices = async (index_pattern) => {
  validateArgs('api.get_indices', { index_pattern, })
  return await client.get(`/indices/${index_pattern}`)
}

api.search = async (index_pattern, body, params) => {
  validateArgs('api.search', { index_pattern, body, })
  return await client.post(`/_search/${index_pattern}`, { data: body, param: params })
}

api.setup = async () => {
  return await client.post(`/setup`)
}

export default api