/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

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

api.isCancel = client.isCancel

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
  const errorType = response?.data?.error?.type
  const index = response?.data?.error?.index

  if (response?.status === 404 && errorType === 'index_not_found_exception' && index?.startsWith('esrs-')) {
    const ctx = getAppContext()
    ctx?.setIsSetup?.(false)
    getHistory().push('/')
    throw new SetupIncompleteError()
  }
  return response
}

////  API: Agent  //////////////////////////////////////////////////////////////

api.chat = async (rounds, inference_id, onChunk, signal, ui_context, id, conversation_id) => {
  inference_id = inference_id || '.rainbow-sprinkles-elastic'
  validateArgs('api.chat', { rounds, inference_id, onChunk, })
  const body = { rounds, inference_id, ui_context, id, conversation_id }

  // We use a local AbortController to manage both the caller's abort signal
  // and our internal activity timeout.
  const controller = new AbortController()
  if (signal) {
    if (signal.aborted) {
      controller.abort()
    } else {
      signal.addEventListener('abort', () => controller.abort())
    }
  }

  // The agent might take a long time to complete a multi-step task, so we don't
  // want a fixed total timeout. Instead, we reset the timeout every time we
  // receive a chunk of data. If we don't receive any data for 300 seconds,
  // we assume the connection has hung and abort it.
  let timeoutId = null
  const resetTimeout = () => {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(() => controller.abort(), 300000)
  }

  // Set the initial timeout for the connection and first response.
  resetTimeout()

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: controller.signal
    })
    if (!response.ok)
      throw new Error(`HTTP error! status: ${response.status}`)
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let chunkCount = 0
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done)
          break

        // Reset the timeout as we successfully received data.
        resetTimeout()

        chunkCount++
        const chunk = decoder.decode(value, { stream: true })
        if (chunk && onChunk)
          onChunk({ data: chunk })
      }
    } finally {
      reader.releaseLock()
    }
    return { status: response.status, data: {} }
  } finally {
    // Clear the timeout to prevent it from firing after the request is finished.
    if (timeoutId) clearTimeout(timeoutId)
  }
}

api.chat_endpoints = async () => {
  validateArgs('api.chat_endpoints', {})
  const response = await client.get(`/api/chat/endpoints`)
  return responseOrFallbackSetup(response)
}

api.chat_cancel = async (session_id) => {
  validateArgs('api.chat_cancel', { session_id })
  const response = await client.post(`/api/chat/cancel/${session_id}`)
  return response
}

////  API: Conversations  //////////////////////////////////////////////////////

api.conversations_search = async (body) => {
  const response = await client.post(`/api/conversations/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.conversations_get = async (conversation_id) => {
  validateArgs('api.conversations_get', { conversation_id, })
  const response = await client.get(`/api/conversations/${conversation_id}`)
  return responseOrFallbackSetup(response)
}

api.conversations_create = async (doc) => {
  validateArgs('api.conversations_create', { doc, })
  const response = await client.post(`/api/conversations`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.conversations_update = async (conversation_id, doc_partial) => {
  validateArgs('api.conversations_update', { conversation_id, doc_partial, })
  const response = await client.put(`/api/conversations/${conversation_id}`, { data: clean(doc_partial) })
  return responseOrFallbackSetup(response)
}

api.conversations_delete = async (conversation_id) => {
  validateArgs('api.conversations_delete', { conversation_id, })
  const response = await client.del(`/api/conversations/${conversation_id}`)
  return responseOrFallbackSetup(response)
}

////  API: Workspaces  /////////////////////////////////////////////////////////

api.workspaces_search = async (body) => {
  const response = await client.post(`/api/workspaces/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.workspaces_get = async (workspace_id) => {
  validateArgs('api.workspaces_get', { workspace_id, })
  const response = await client.get(`/api/workspaces/${workspace_id}`)
  return responseOrFallbackSetup(response)
}

api.workspaces_create = async (doc) => {
  validateArgs('api.workspaces_create', { doc, })
  const response = await client.post(`/api/workspaces`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.workspaces_update = async (workspace_id, doc_partial) => {
  validateArgs('api.workspaces_update', { workspace_id, doc_partial, })
  const response = await client.put(`/api/workspaces/${workspace_id}`, { data: clean(doc_partial) })
  return responseOrFallbackSetup(response)
}

api.workspaces_delete = async (workspace_id) => {
  validateArgs('api.workspaces_delete', { workspace_id, })
  const response = await client.del(`/api/workspaces/${workspace_id}`)
  return responseOrFallbackSetup(response)
}


////  API: Displays  ///////////////////////////////////////////////////////////

api.displays_search = async (workspace_id, body) => {
  validateArgs('api.displays_search', { workspace_id, })
  const response = await client.post(`/api/workspaces/${workspace_id}/displays/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.displays_get = async (workspace_id, display_id) => {
  validateArgs('api.displays_get', { workspace_id, display_id, })
  const response = await client.get(`/api/workspaces/${workspace_id}/displays/${display_id}`)
  return responseOrFallbackSetup(response)
}

api.displays_create = async (workspace_id, doc) => {
  validateArgs('api.displays_create', { workspace_id, doc, })
  const response = await client.post(`/api/workspaces/${workspace_id}/displays`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.displays_update = async (workspace_id, display_id, doc_partial) => {
  validateArgs('api.displays_update', { workspace_id, display_id, doc_partial, })
  const response = await client.put(`/api/workspaces/${workspace_id}/displays/${display_id}`, { data: clean(doc_partial) })
  return responseOrFallbackSetup(response)
}

api.displays_delete = async (workspace_id, display_id) => {
  validateArgs('api.displays_delete', { workspace_id, display_id, })
  const response = await client.del(`/api/workspaces/${workspace_id}/displays/${display_id}`)
  return responseOrFallbackSetup(response)
}


////  API: Scenarios  //////////////////////////////////////////////////////////

api.scenarios_search = async (workspace_id, body) => {
  validateArgs('api.scenarios_search', { workspace_id, })
  const response = await client.post(`/api/workspaces/${workspace_id}/scenarios/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.scenarios_tags = async (workspace_id) => {
  validateArgs('api.scenarios_tags', { workspace_id, })
  const response = await client.get(`/api/workspaces/${workspace_id}/scenarios/_tags`)
  return responseOrFallbackSetup(response)
}

api.scenarios_get = async (workspace_id, scenario_id) => {
  validateArgs('api.scenarios_get', { workspace_id, scenario_id, })
  const response = await client.get(`/api/workspaces/${workspace_id}/scenarios/${scenario_id}`)
  return responseOrFallbackSetup(response)
}

api.scenarios_create = async (workspace_id, doc) => {
  validateArgs('api.scenarios_create', { workspace_id, doc, })
  const response = await client.post(`/api/workspaces/${workspace_id}/scenarios`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.scenarios_update = async (workspace_id, scenario_id, doc_partial) => {
  validateArgs('api.scenarios_update', { workspace_id, scenario_id, doc_partial, })
  const response = await client.put(`/api/workspaces/${workspace_id}/scenarios/${scenario_id}`, { data: clean(doc_partial) })
  return responseOrFallbackSetup(response)
}

api.scenarios_delete = async (workspace_id, scenario_id) => {
  validateArgs('api.scenarios_delete', { workspace_id, scenario_id, })
  const response = await client.del(`/api/workspaces/${workspace_id}/scenarios/${scenario_id}`)
  return responseOrFallbackSetup(response)
}


////  API: Judgements  /////////////////////////////////////////////////////////

api.judgements_search = async (workspace_id, scenario_id, body, params) => {
  validateArgs('api.judgements_search', { workspace_id, scenario_id, body, })
  body.workspace_id = workspace_id
  body.scenario_id = scenario_id
  const response = await client.post(`/api/workspaces/${workspace_id}/judgements/_search`, { data: body, params: params })
  return responseOrFallbackSetup(response)
}

api.judgements_set = async (workspace_id, scenario_id, doc) => {
  validateArgs('api.judgements_set', { workspace_id, scenario_id, doc, })
  doc.workspace_id = workspace_id
  doc.scenario_id = scenario_id
  const response = await client.put(`/api/workspaces/${workspace_id}/judgements`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.judgements_unset = async (workspace_id, judgement_id) => {
  validateArgs('api.judgements_unset', { workspace_id, judgement_id, })
  const response = await client.del(`/api/workspaces/${workspace_id}/judgements/${judgement_id}`)
  return responseOrFallbackSetup(response)
}


////  API: Strategies  /////////////////////////////////////////////////////////

api.strategies_search = async (workspace_id, body) => {
  validateArgs('api.strategies_search', { workspace_id, })
  const response = await client.post(`/api/workspaces/${workspace_id}/strategies/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.strategies_tags = async (workspace_id) => {
  validateArgs('api.strategies_tags', { workspace_id, })
  const response = await client.get(`/api/workspaces/${workspace_id}/strategies/_tags`)
  return responseOrFallbackSetup(response)
}

api.strategies_get = async (workspace_id, strategy_id) => {
  validateArgs('api.strategies_get', { workspace_id, strategy_id, })
  const response = await client.get(`/api/workspaces/${workspace_id}/strategies/${strategy_id}`)
  return responseOrFallbackSetup(response)
}

api.strategies_create = async (workspace_id, doc) => {
  validateArgs('api.strategies_create', { workspace_id, doc, })
  const response = await client.post(`/api/workspaces/${workspace_id}/strategies`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.strategies_update = async (workspace_id, strategy_id, doc_partial) => {
  validateArgs('api.strategies_update', { workspace_id, strategy_id, doc_partial, })
  const response = await client.put(`/api/workspaces/${workspace_id}/strategies/${strategy_id}`, { data: clean(doc_partial) })
  return responseOrFallbackSetup(response)
}

api.strategies_delete = async (workspace_id, strategy_id) => {
  validateArgs('api.strategyies_delete', { workspace_id, strategy_id, })
  const response = await client.del(`/api/workspaces/${workspace_id}/strategies/${strategy_id}`)
  return responseOrFallbackSetup(response)
}


////  API: Benchmarks  /////////////////////////////////////////////////////////

api.benchmarks_search = async (workspace_id, body) => {
  validateArgs('api.benchmarks_search', { workspace_id, })
  const response = await client.post(`/api/workspaces/${workspace_id}/benchmarks/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.benchmarks_tags = async (workspace_id) => {
  validateArgs('api.benchmarks_tags', { workspace_id, })
  const response = await client.get(`/api/workspaces/${workspace_id}/benchmarks/_tags`)
  return responseOrFallbackSetup(response)
}

api.benchmarks_get = async (workspace_id, benchmark_id) => {
  validateArgs('api.benchmarks_get', { workspace_id, benchmark_id, })
  const response = await client.get(`/api/workspaces/${workspace_id}/benchmarks/${benchmark_id}`)
  return responseOrFallbackSetup(response)
}

api.benchmarks_create = async (workspace_id, doc) => {
  validateArgs('api.benchmarks_create', { workspace_id, doc, })
  const response = await client.post(`/api/workspaces/${workspace_id}/benchmarks`, { data: clean(doc) })
  return responseOrFallbackSetup(response)
}

api.benchmarks_update = async (workspace_id, benchmark_id, doc_partial) => {
  validateArgs('api.benchmarks_update', { workspace_id, benchmark_id, doc_partial, })
  const response = await client.put(`/api/workspaces/${workspace_id}/benchmarks/${benchmark_id}`, { data: clean(doc_partial) })
  return responseOrFallbackSetup(response)
}

api.benchmarks_delete = async (workspace_id, benchmark_id) => {
  validateArgs('api.benchmarks_delete', { workspace_id, benchmark_id, })
  const response = await client.del(`/api/workspaces/${workspace_id}/benchmarks/${benchmark_id}`)
  return responseOrFallbackSetup(response)
}

api.benchmarks_make_candidate_pool = async (workspace_id, body) => {
  validateArgs('api.benchmarks_make_candidate_pool', { workspace_id, body })
  const response = await client.post(`/api/workspaces/${workspace_id}/benchmarks/_candidates`, { data: body })
  return responseOrFallbackSetup(response)
}


////  API: Evaluations  ////////////////////////////////////////////////////////

api.evaluations_search = async (workspace_id, benchmark_id, body) => {
  validateArgs('api.evaluations_search', { workspace_id, benchmark_id, })
  const response = await client.post(`/api/workspaces/${workspace_id}/benchmarks/${benchmark_id}/evaluations/_search`, body ? { data: body } : {})
  return responseOrFallbackSetup(response)
}

api.evaluations_get = async (workspace_id, benchmark_id, evaluation_id) => {
  validateArgs('api.evaluations_get', { workspace_id, benchmark_id, evaluation_id, })
  const response = await client.get(`/api/workspaces/${workspace_id}/benchmarks/${benchmark_id}/evaluations/${evaluation_id}`)
  return responseOrFallbackSetup(response)
}

api.evaluations_create = async (workspace_id, benchmark_id, body) => {
  validateArgs('api.evaluations_create', { workspace_id, benchmark_id, body, })
  const response = await client.post(`/api/workspaces/${workspace_id}/benchmarks/${benchmark_id}/evaluations`, { data: clean(body) })
  return responseOrFallbackSetup(response)
}

api.evaluations_run = async (workspace_id, body) => {
  validateArgs('api.evaluations_run', { workspace_id, body, })
  const response = await client.post(`/api/workspaces/${workspace_id}/evaluations/_run`, { data: body })
  return responseOrFallbackSetup(response)
}

api.evaluations_delete = async (workspace_id, benchmark_id, evaluation_id) => {
  validateArgs('api.evaluations_delete', { workspace_id, benchmark_id, evaluation_id, })
  const response = await client.del(`/api/workspaces/${workspace_id}/benchmarks/${benchmark_id}/evaluations/${evaluation_id}`)
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

api.upgrade_run = async () => {
  return await client.post(`/api/upgrade`)
}

export default api