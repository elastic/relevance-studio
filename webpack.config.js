/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

const path = require('path')
const fs = require('fs')
const http = require('http')
const CopyWebpackPlugin = require('copy-webpack-plugin')
const HtmlWebpackPlugin = require('html-webpack-plugin')

const HTTP_DEV_PORT = 8080
const HTTPS_DEV_PORT = 8443

function parseBool(value, defaultValue = true) {
  if (value == null || String(value).trim() === '') return defaultValue
  return ['1', 'true', 'yes', 'on'].includes(String(value).trim().toLowerCase())
}

function parseDotEnv(filePath) {
  if (!fs.existsSync(filePath)) return {}

  const out = {}
  const lines = fs.readFileSync(filePath, 'utf8').split(/\r?\n/)
  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    const separatorIndex = line.indexOf('=')
    if (separatorIndex === -1) continue

    const key = line.slice(0, separatorIndex).trim()
    let value = line.slice(separatorIndex + 1).trim()
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1)
    }
    out[key] = value
  }

  return out
}

const fileEnv = {
  ...parseDotEnv(path.resolve(__dirname, '.env-reference')),
  ...parseDotEnv(path.resolve(__dirname, '.env')),
}

function envValue(key) {
  return process.env[key] ?? fileEnv[key]
}

function getProxyTarget() {
  if (process.env.DEV_API_URL) {
    return process.env.DEV_API_URL
  }
  const tlsEnabled = parseBool(envValue('TLS_ENABLED'), true)
  const backendPort = envValue('FLASK_RUN_PORT') || '4096'
  const protocol = tlsEnabled ? 'https' : 'http'
  return `${protocol}://localhost:${backendPort}`
}

function shouldVerifyTlsCert(target) {
  if (!target.startsWith('https')) return false
  return parseBool(envValue('DEV_API_STRICT_TLS'), false)
}

function resolveFilePath(filePath) {
  if (!filePath) return null
  return path.isAbsolute(filePath) ? filePath : path.resolve(__dirname, filePath)
}

function getDevServerProtocol() {
  return parseBool(envValue('TLS_ENABLED'), true) ? 'https' : 'http'
}

function getDevServerPort() {
  return getDevServerProtocol() === 'https' ? HTTPS_DEV_PORT : HTTP_DEV_PORT
}

function getDevServerServerConfig() {
  if (getDevServerProtocol() !== 'https') return 'http'

  const certPath = resolveFilePath(envValue('TLS_CERT_FILE'))
  const keyPath = resolveFilePath(envValue('TLS_KEY_FILE'))

  // When cert paths are configured and available, use them for webpack HTTPS.
  if (
    certPath &&
    keyPath &&
    fs.existsSync(certPath) &&
    fs.existsSync(keyPath)
  ) {
    return {
      type: 'https',
      options: {
        cert: fs.readFileSync(certPath),
        key: fs.readFileSync(keyPath),
      },
    }
  }

  // Fallback to webpack-dev-server generated HTTPS certificate.
  return 'https'
}

let httpRedirectServer = null

function startHttpRedirectServer() {
  const redirectPort = HTTP_DEV_PORT
  const httpsPort = HTTPS_DEV_PORT
  if (httpRedirectServer) return

  httpRedirectServer = http.createServer((req, res) => {
    const requestHost = req.headers.host || `localhost:${redirectPort}`
    const hostname = requestHost.split(':')[0]
    const location = `https://${hostname}:${httpsPort}${req.url || '/'}`
    res.statusCode = 308
    res.setHeader('Location', location)
    res.end(`Redirecting to ${location}`)
  })

  httpRedirectServer.on('error', (err) => {
    console.warn(
      `[dev-redirect] Failed to start HTTP redirect server on port ${redirectPort}: ${err.message}`
    )
    httpRedirectServer = null
  })

  httpRedirectServer.listen(redirectPort, () => {
    console.log(
      `[dev-redirect] http://localhost:${redirectPort} -> https://localhost:${httpsPort}`
    )
  })
}

module.exports = {
  entry: ['./src/ui/js/index.js'],
  output: {
    filename: 'main.js',
    path: path.resolve(__dirname, 'dist'),
    publicPath: '/'
  },
  module: {
    rules: [
      {
        test: /\.(js|tsx?)$/,
        use: 'babel-loader',
        exclude: /node_modules/
      },
      {
        test: /\.css$/,
        use: [
          {
              loader: 'style-loader'
          },
          {
              loader: 'css-loader'
          }
        ]
      },
      {
        test: /\.(woff|woff2|ttf|eot|ico|png|gif|jpg|jpeg)(\?|$)/,
        use: 'file-loader'
      },
      {
        test: /\.html$/,
        use: 'html-loader'
      }
    ]
  },
  plugins: [
    new HtmlWebpackPlugin({
        template: './src/ui/index.html'
    }),
    new CopyWebpackPlugin({
      patterns: [
        {
          from: path.resolve(__dirname, 'src/ui/img'),
          to: path.resolve(__dirname, 'dist/img')
        },
        {
          from: path.resolve(__dirname, 'node_modules/monaco-editor/min'),
          to: path.resolve(__dirname, 'dist/monaco-editor/min')
        }
      ]
    })
  ],
  resolve: {
    extensions: ['.js', '.jsx'],
  },
  devServer: {
    port: getDevServerPort(),
    server: getDevServerServerConfig(),
    onListening: (devServer) => {
      if (getDevServerProtocol() !== 'https') return
      startHttpRedirectServer()
    },
    static: {
      directory: path.join(__dirname, 'dist'),
    },
    // DEV_API_URL: optional override for API proxy target.
    // By default, infer protocol from TLS_ENABLED and port from FLASK_RUN_PORT.
    proxy: (() => {
      const target = getProxyTarget()
      const secure = shouldVerifyTlsCert(target)
      return [
        {
          context: ['/api/chat'],
          target,
          changeOrigin: true,
          secure,
          proxyTimeout: 300000,
          timeout: 300000,
        },
        {
          context: ['**', '!**.js', '!/api/chat'],
          target,
          secure,
        },
      ]
    })(),
    compress: false
  }
}