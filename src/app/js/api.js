/**
 * api.js
 * 
 * Implements API requests implemented by the esreef server.
 */

import { EuiText } from '@elastic/eui'
import client from './client'

const api = {}

/**
 * Template for toasts for error messages.
 */
api.errorToast = (err, props) => {
  console.warn('api.errorToast')
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

////  Projects  ////////////////////////////////////////////////////////////////

api.get_projects = async () => {
  return await client.get(`/projects`)
}

api.get_project = async (project_id) => {
  return await client.get(`/projects/${project_id}`)
}

api.create_project = async (doc) => {
  return await client.post(`/projects`, { data: doc })
}

api.update_project = async (project_id, doc) => {
  return await client.put(`/projects/${project_id}`, { data: doc })
}

api.delete_project = async (project_id) => {
  return await client.del(`/projects/${project_id}`)
}


////  Displays  ////////////////////////////////////////////////////////////////

api.get_displays = async (project_id) => {
  return await client.get(`/projects/${project_id}/displays`)
}

api.get_display = async (project_id, display_id) => {
  return await client.get(`/projects/${project_id}/displays/${display_id}`)
}

api.create_display = async (project_id, doc) => {
  return await client.post(`/projects/${project_id}/displays`, { data: doc })
}

api.update_display = async (project_id, display_id, doc) => {
  return await client.put(`/projects/${project_id}/displays/${display_id}`, { data: doc })
}

api.delete_display = async (project_id, display_id) => {
  return await client.del(`/projects/${project_id}/displays/${display_id}`)
}


////  Scenarios  ///////////////////////////////////////////////////////////////

api.get_scenarios = async (project_id) => {
  return await client.get(`/projects/${project_id}/scenarios`)
}

api.get_scenario = async (project_id, scenario_id) => {
  return await client.get(`/projects/${project_id}/scenarios/${scenario_id}`)
}

api.create_scenario = async (project_id, doc) => {
  return await client.post(`/projects/${project_id}/scenarios`, { data: doc })
}

api.update_scenario = async (project_id, scenario_id, doc) => {
  return await client.put(`/projects/${project_id}/scenarios/${scenario_id}`, { data: doc })
}

api.delete_scenario = async (project_id, scenario_id) => {
  return await client.del(`/projects/${project_id}/scenarios/${scenario_id}`)
}


////  Judgements  //////////////////////////////////////////////////////////////

api.get_judgements_docs = async (project_id, scenario_id, body, params) => {
  return await client.post(`/projects/${project_id}/scenarios/${scenario_id}/judgements/_docs`, { data: body, params: params })
}

api.get_judgements = async (project_id) => {
  return await client.get(`/projects/${project_id}/judgements`)
}

api.get_judgement = async (project_id, judgement_id) => {
  return await client.get(`/projects/${project_id}/judgements/${judgement_id}`)
}

api.set_judgement = async (project_id, scenario_id, doc) => {
  return await client.put(`/projects/${project_id}/scenarios/${scenario_id}/judgements`, { data: doc })
}

api.unset_judgement = async (project_id, scenario_id, doc) => {
  return await client.del(`/projects/${project_id}/scenarios/${scenario_id}/judgements`, { data: doc })
}


////  Strategies  //////////////////////////////////////////////////////////////

api.get_strategies = async (project_id) => {
  return await client.get(`/projects/${project_id}/strategies`)
}

api.get_strategy = async (project_id, strategy_id) => {
  return await client.get(`/projects/${project_id}/strategies/${strategy_id}`)
}

api.create_strategy = async (project_id, doc) => {
  return await client.post(`/projects/${project_id}/strategies`, { data: doc })
}

api.update_strategy = async (project_id, strategy_id, doc) => {
  return await client.put(`/projects/${project_id}/strategies/${strategy_id}`, { data: doc })
}

api.delete_strategy = async (project_id, strategy_id) => {
  return await client.del(`/projects/${project_id}/strategies/${strategy_id}`)
}


////  Evaluations  /////////////////////////////////////////////////////////////

api.get_evaluations = async (project_id) => {
  return await client.get(`/projects/${project_id}/evaluations`)
}

api.get_evaluation = async (project_id, evaluation_id) => {
  return await client.get(`/projects/${project_id}/evaluations/${evaluation_id}`)
}

api.run_evaluation = async (project_id, body, params) => {
  return await client.post(`/projects/${project_id}/evaluations`, { data: body, params: params })
}

api.delete_evaluation = async (project_id, evaluation_id) => {
  return await client.del(`/projects/${project_id}/evaluations/${evaluation_id}`)
}


////  Other  ///////////////////////////////////////////////////////////////////

api.get_indices = async (index_pattern) => {
  return await client.get(`/indices/${index_pattern}`)
}

api.search = async (index_pattern, body, params) => {
  return await client.post(`/_search/${index_pattern}`, { data: body, param: params })
}

api.setup = async () => {
  return await client.post(`/setup`)
}

export default api