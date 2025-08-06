/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

/**
 * client.js
 * 
 * A low-level REST client used primarily by api.js.
 */

import axios from 'axios'
import { getAppContext } from './Contexts/AppContext'

/**
 * Handle non-API network errors such as net::ERR_CONNECTION_REFUSED.
 */
axios.interceptors.response.use(
  async (response) => response,
  async (error) => {
    if (!error.response) {
      const app = getAppContext()
      if (app?.addToast) {
        app.addToast({
          title: error.response?.statusText || 'Network error',
          color: 'danger',
          iconType: 'alert',
          text: <p>{error.message || 'An unexpected error occurred'}</p>,
        })
      }
    }
    return Promise.reject(error)
  }
)

/**
 * Submit a request to the server.
 */
const request = async (path, opts) => {
  opts = opts || {}
  return await axios.request({
    method: opts.method,
    url: path,
    params: opts.params,
    headers: opts.headers || {},
    data: opts.data,
    validateStatus: (status) => (status >= 200 && status < 400) || status == 404,
    timeout: opts.timeout || 60000,
  })
}

const del = async (path, opts) => {
  opts = opts || {}
  opts.method = 'DELETE'
  return await request(path, opts)
}

const get = async (path, opts) => {
  opts = opts || {}
  opts.method = 'GET'
  return await request(path, opts)
}

const post = async (path, opts) => {
  opts = opts || {}
  opts.method = 'POST'
  return await request(path, opts)
}

const put = async (path, opts) => {
  opts = opts || {}
  opts.method = 'PUT'
  return await request(path, opts)
}

const client = {
  request: request,
  del: del,
  get: get,
  post: post,
  put: put,
}

export default client