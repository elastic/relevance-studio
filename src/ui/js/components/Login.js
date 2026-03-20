/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useState } from 'react'
import {
  EuiButton,
  EuiFieldPassword,
  EuiFieldText,
  EuiFlexGroup,
  EuiFlexItem,
  EuiForm,
  EuiFormRow,
  EuiHorizontalRule,
  EuiIcon,
  EuiLink,
  EuiPanel,
  EuiSpacer,
  EuiText,
  EuiTitle,
} from '@elastic/eui'
import { useAppContext } from '../Contexts/AppContext'
import { useAuthContext } from '../Contexts/AuthContext'
import { getHistory } from '../history'
import { APP_LOGO_ICON_DARK, APP_LOGO_ICON_LIGHT } from '../Layout/Page'

const Login = () => {
  const { login } = useAuthContext()
  const { darkMode } = useAppContext()
  const history = getHistory()

  const [view, setView] = useState('select') // 'select' | 'form'
  const [mode, setMode] = useState('basic')  // 'basic' | 'apikey'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)
    try {
      const credentials = mode === 'basic'
        ? { username, password }
        : { api_key: apiKey }
      await login(credentials)
      const from = history.location.state?.from?.pathname || '/'
      history.replace(from)
    } catch (err) {
      const msg = err.response?.data?.message || err.message || 'Login failed'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const selectMethod = (method) => {
    setMode(method)
    setError(null)
    setView('form')
  }

  const goBack = () => {
    setError(null)
    setView('select')
  }

  const logo = (
    <div style={{ textAlign: 'center' }}>
      <EuiIcon
        type={darkMode ? APP_LOGO_ICON_DARK : APP_LOGO_ICON_LIGHT}
        size="xxl"
      />
      <EuiSpacer size="m" />
      <EuiTitle size="m">
        <h1>Elasticsearch Relevance Studio</h1>
      </EuiTitle>
    </div>
  )

  return (
    <div style={{
      alignItems: 'center',
      display: 'flex',
      height: '100vh',
      justifyContent: 'center',
      padding: '24px',
    }}>
      <div style={{ maxWidth: 400, width: '100%' }}>
        {logo}
        <EuiSpacer size="s" />
        <EuiText color="subdued" size="s" style={{ textAlign: 'center' }}>
          Login using your credentials for the <a href="https://elastic.github.io/relevance-studio/#/docs/latest/reference/architecture?id=studio-deployment" target="_blank">studio deployment</a>.
        </EuiText>
        <EuiSpacer size="xl" />

        {view === 'select' ? (
          <EuiPanel paddingSize="none">
            <button
              type="button"
              onClick={() => selectMethod('basic')}
              style={{ display: 'block', width: '100%', padding: '16px', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left' }}
            >
              <EuiFlexGroup alignItems="center" gutterSize="m" responsive={false}>
                <EuiFlexItem grow={false}>
                  <EuiIcon type="user" size="l" color="primary" />
                </EuiFlexItem>
                <EuiFlexItem>
                  <EuiTitle size="xs" style={{ fontWeight: 500 }}><p>Log in with username and password</p></EuiTitle>
                </EuiFlexItem>
              </EuiFlexGroup>
            </button>
            <EuiHorizontalRule margin="none" />
            <button
              type="button"
              onClick={() => selectMethod('apikey')}
              style={{ display: 'block', width: '100%', padding: '16px', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left' }}
            >
              <EuiFlexGroup alignItems="center" gutterSize="m" responsive={false}>
                <EuiFlexItem grow={false}>
                  <EuiIcon type="key" size="l" color="primary" />
                </EuiFlexItem>
                <EuiFlexItem>
                  <EuiTitle size="xs" style={{ fontWeight: 500 }}><p>Log in with API key</p></EuiTitle>
                </EuiFlexItem>
              </EuiFlexGroup>
            </button>
          </EuiPanel>
        ) : (
          <EuiPanel paddingSize="l">
            <EuiForm component="form" onSubmit={handleSubmit}>
              {mode === 'basic' ? (
                <>
                  <EuiFormRow label="Username" isInvalid={!!error}>
                    <EuiFieldText
                      name="username"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      autoComplete="username"
                      isInvalid={!!error}
                      disabled={isLoading}
                    />
                  </EuiFormRow>
                  <EuiFormRow label="Password" isInvalid={!!error}>
                    <EuiFieldPassword
                      name="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete="current-password"
                      type="dual"
                      isInvalid={!!error}
                      disabled={isLoading}
                    />
                  </EuiFormRow>
                </>
              ) : (
                <EuiFormRow
                  label="API key"
                  helpText={<>Base64-encoded <a href="https://www.elastic.co/docs/deploy-manage/api-keys/elasticsearch-api-keys" target="_blank">Elasticsearch API Key</a></>}
                  isInvalid={!!error}
                >
                  <EuiFieldPassword
                    name="api_key"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    type="dual"
                    isInvalid={!!error}
                    disabled={isLoading}
                  />
                </EuiFormRow>
              )}
              {error && (
                <>
                  <EuiSpacer size="s" />
                  <EuiText color="danger" size="s">{error}</EuiText>
                </>
              )}
              <EuiSpacer size="l" />
              <EuiFlexGroup alignItems="center" responsive={false}>
                <EuiFlexItem>
                  <EuiButton
                    type="submit"
                    fill
                    fullWidth
                    isLoading={isLoading}
                    isDisabled={mode === 'basic' ? !(username && password) : !apiKey}
                  >
                    Log in
                  </EuiButton>
                </EuiFlexItem>
                <EuiFlexItem grow={false}>
                  <EuiLink onClick={goBack}>More login options</EuiLink>
                </EuiFlexItem>
              </EuiFlexGroup>
            </EuiForm>
          </EuiPanel>
        )}
      </div>
    </div>
  )
}

export default Login
