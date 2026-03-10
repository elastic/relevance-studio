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

import { createElement } from 'react'
import axios from 'axios'
import { getAppContext } from './Contexts/AppContext'
import { get401Handler } from './auth401handler'
import { getHistory } from './history'

/**
 * Handle 401: clear auth state and redirect to login.
 */
axios.interceptors.response.use(
  async (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const path = error.config?.url || ''
      if (!path.includes('/api/auth/login') && !path.includes('/api/auth/logout')) {
        const handler = get401Handler()
        if (handler) {
          handler()
        } else {
          getHistory().replace('/login')
        }
      }
    }
    if (!error.response) {
      const app = getAppContext()
      if (app?.addToast) {
        app.addToast({
          title: 'Network error',
          color: 'danger',
          iconType: 'alert',
          text: createElement('p', null, error.message || 'An unexpected error occurred'),
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
    signal: opts.signal,
    onDownloadProgress: (e) => {
      if (opts.onDownloadProgress) {
        const response = e.event?.currentTarget?.response || ''; // Access raw response and ensure it's a string
        if (response) {
          if (!opts._lastResponseLength) opts._lastResponseLength = 0
          const chunk = response.substring(opts._lastResponseLength)
          opts._lastResponseLength = response.length
          if (chunk) {
            opts.onDownloadProgress({ data: chunk })
          }
        }
      }
    },
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
  isCancel: axios.isCancel,
}

export default client