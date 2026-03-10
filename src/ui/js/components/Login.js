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
  EuiForm,
  EuiFormRow,
  EuiPanel,
  EuiSpacer,
  EuiSwitch,
  EuiText,
  EuiTitle,
} from '@elastic/eui'
import { useAuthContext } from '../Contexts/AuthContext'
import { getHistory } from '../history'

const Login = () => {
  const { login } = useAuthContext()
  const history = getHistory()

  const [mode, setMode] = useState('basic') // 'basic' | 'apikey'
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

  return (
    <div style={{
      alignItems: 'center',
      display: 'flex',
      height: '100vh',
      justifyContent: 'center',
      padding: '24px',
    }}>
      <EuiPanel paddingSize="xl" style={{ maxWidth: 400 }}>
        <EuiTitle size="m">
          <h1>Sign in</h1>
        </EuiTitle>
        <EuiSpacer size="l" />
        <EuiForm component="form" onSubmit={handleSubmit}>
          <EuiFormRow label="Sign in with" hasChildLabel={false}>
            <EuiSwitch
              label={mode === 'basic' ? 'Username & password' : 'API key'}
              checked={mode === 'apikey'}
              onChange={(e) => {
                setMode(e.target.checked ? 'apikey' : 'basic')
                setError(null)
              }}
            />
          </EuiFormRow>
          <EuiSpacer size="m" />
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
                  isInvalid={!!error}
                  disabled={isLoading}
                />
              </EuiFormRow>
            </>
          ) : (
            <EuiFormRow
              label="API key"
              helpText="Base64-encoded id:api_key"
              isInvalid={!!error}
            >
              <EuiFieldPassword
                name="api_key"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="base64-encoded API key"
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
          <EuiButton
            type="submit"
            fill
            isLoading={isLoading}
            isDisabled={mode === 'basic' ? !(username && password) : !apiKey}
          >
            Sign in
          </EuiButton>
        </EuiForm>
      </EuiPanel>
    </div>
  )
}

export default Login
