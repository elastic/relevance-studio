/**
 * client.js
 * 
 * A low-level REST client used primarily by api.js.
 */

import axios from 'axios'
import { getAppContext } from './Contexts/AppContext'

const TARGET_REQUEST_DELAY = 0 // Set to 500 to reduce flickering from fast loading

/**
 * Sleep for some number of milliseconds (ms).
 */
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * Generate a random number of milliseconds within 50% of a given target.
 */
const randomMillis = (target) => {
  const max = target * 1.5
  const min = target * 0.5
  return Math.random() * (max - min) + min
}

/**
 * Track the start time of each request.
 */
axios.interceptors.request.use(
  async (config) => {
    config.startTime = new Date().getTime()
    return config
  },
  (error) => Promise.reject(error)
)

/**
 * Ensure a proper delay for each request and then process the response data.
 */
axios.interceptors.response.use(
  async (response) => {
    // Ensure the each request has some noticable latency as feedback to the user.
    // If the elapsed time between now and the given startTime is less than that
    // target amount, impose a delay for the remaining difference.
    const timeElapsed = new Date().getTime() - response.config.startTime
    const timeRemaining = randomMillis(TARGET_REQUEST_DELAY) - timeElapsed
    if (timeElapsed > 0) await sleep(timeRemaining)
    return response
  },
  async (error) => {
    // Ensure the each request has some noticable latency as feedback to the user.
    // If the elapsed time between now and the given startTime is less than that
    // target amount, impose a delay for the remaining difference.
    const timeElapsed = new Date().getTime() - error.config.startTime
    const timeRemaining = randomMillis(TARGET_REQUEST_DELAY) - timeElapsed
    if (timeElapsed > 0) await sleep(timeRemaining)

    // Handle non-API network errors such as net::ERR_CONNECTION_REFUSED.
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
    timeout: 4000, // TODO: Make configurable
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