/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useState } from 'react'
import {
  EuiButton,
  EuiCallOut,
  EuiCode,
  EuiIcon,
  EuiPanel,
  EuiProgress,
  EuiSpacer,
  EuiTitle,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { Page } from '../../Layout'
import { getHistory } from '../../history'
import api from '../../api'

const Home = () => {

  const history = getHistory()

  ////  Context  ///////////////////////////////////////////////////////////////

  const {
    addToast,
    darkMode,
    deploymentMode,
    isCheckingSetup,
    isSetup,
    hasCheckedSetup,
    setIsSetup,
  } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [isProcessing, setIsProcessing] = useState(false)

  ////  Handlers  //////////////////////////////////////////////////////////////

  const onSetup = async () => {
    try {
      setIsProcessing(true)
      const response = await api.setup_run()

      if ((response?.data?.failures ?? 0) === 0) {
        setIsSetup(true)
        addToast({ color: 'success', title: 'Setup complete!' })
      } else {
        setIsSetup(false)
        addToast({
          color: 'danger',
          title: 'Setup incomplete',
          text: (
            <EuiText size='xs' color='subdued'>
              Failed to setup one or more index templates or indices.
            </EuiText>
          ),
        })
      }
    } catch (e) {
      addToast(api.errorToast(e, { title: 'Failed to run setup' }))
      setIsSetup(false)
    } finally {
      setIsProcessing(false)
    }
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  if (isCheckingSetup)
    return <EuiProgress color='accent' position='fixed' size='s' />

  const renderConnectionFailure = () => (
    <EuiPanel grow={false} paddingSize='xl' style={{ margin: '0 auto', width: 600, textAlign: 'center' }}>
      <EuiIcon color="subdued" type="cloudDrizzle" size="l" />
      <EuiSpacer size="l" />
      <EuiTitle size="m">
        <h3>Studio Deployment Unreachable</h3>
      </EuiTitle>
      <EuiSpacer size="l" />
      <EuiText size="s">
        <p>
          Reload this page after the <span style={{ fontWeight: 500 }}>Studio Deployment</span> is reachable by the <span style={{ fontWeight: 500 }}>Server</span>.
          <br />
          Read the <a href="https://elastic.github.io/relevance-studio/#/docs/guide/quickstart" target="_blank">setup</a> and <a href="https://elastic.github.io/relevance-studio/#/docs/reference/architecture" target="_blank">architecture</a> documentation for help.
        </p>
      </EuiText>
    </EuiPanel>
  )

  const renderSetupPrompt = () => (
    <EuiPanel grow={false} paddingSize='xs' style={{ margin: '0 auto', width: 600 }}>
      <EuiCallOut color='primary'>
        <EuiText>
          <p>
            You're almost ready! Just click setup to finish.
          </p>
        </EuiText>
        <EuiSpacer />
        <EuiButton
          color='primary'
          disabled={isProcessing}
          fill
          isLoading={isProcessing}
          onClick={onSetup}
        >
          Setup
        </EuiButton>
        <EuiSpacer />
        <EuiText size='xs'>
          <p>
            This will create the <EuiCode style={{ padding: '0 2px' }} transparentBackground>esrs-*</EuiCode> index templates and indices.
          </p>
        </EuiText>
      </EuiCallOut>
    </EuiPanel>
  )

  const renderHomePrompt = () => (
    <EuiPanel grow={false} paddingSize='xs' style={{ margin: '0 auto', width: 600 }}>
      <EuiCallOut color='primary'>
        <EuiText>
          <p>
            Get started by creating a workspace.
          </p>
        </EuiText>
        <EuiSpacer />
        <EuiButton
          color='primary'
          fill
          onClick={() => history.push('/workspaces')}
        >
          Go to workspaces
        </EuiButton>
      </EuiCallOut>
    </EuiPanel>
  )

  return (
    <Page>
      <EuiPanel color='transparent'>
        <div style={{ textAlign: 'center' }}>
          <EuiSpacer />
          {hasCheckedSetup && !deploymentMode && renderConnectionFailure()}
          {hasCheckedSetup && !!deploymentMode &&
            <>
              <EuiTitle size='l'>
                <h1 style={{ fontWeight: 700 }}>
                  <big>Welcome!</big>
                </h1>
              </EuiTitle>
              <EuiSpacer />
              <EuiText>
                <p>
                  Let's create amazing search experiences.
                </p>
              </EuiText>
              <EuiSpacer size='l' />
              <EuiPanel color='transparent' paddingSize='xl'>
                <img src={darkMode ? '/img/process-white.png' : '/img/process.png'} width={600} />
              </EuiPanel>
              <EuiSpacer size='l' />
              {!isSetup ? renderSetupPrompt() : renderHomePrompt()}
            </>
          }
        </div>
      </EuiPanel>
    </Page>
  )
}

export default Home