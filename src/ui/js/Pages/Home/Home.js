/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useState } from 'react'
import {
  EuiButton,
  EuiCode,
  EuiIcon,
  EuiInMemoryTable,
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
    isUpgradeNeeded,
    isSetup,
    hasCheckedSetup,
    setIsSetup,
    setIsUpgradeNeeded,
    setUpgradeState,
    upgradeState,
  } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [isProcessing, setIsProcessing] = useState(false)
  const [isUpgrading, setIsUpgrading] = useState(false)
  const pendingSteps = (upgradeState?.pending_steps || []).map((step, idx) => ({
    ...step,
    _rowId: `${step.version}-${step.template}-${idx}`,
  }))

  ////  Handlers  //////////////////////////////////////////////////////////////

  const onSetup = async () => {
    try {
      setIsProcessing(true)
      const response = await api.setup_run()

      if ((response?.data?.setup?.failures ?? 0) === 0) {
        setIsSetup(true)
        const setupResponse = await api.setup_check()
        const upgrade = setupResponse?.data?.upgrade || {}
        setIsUpgradeNeeded(Boolean(upgrade?.upgrade_needed))
        setUpgradeState(upgrade)
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

  const onUpgrade = async () => {
    try {
      setIsUpgrading(true)
      const response = await api.upgrade_run()
      if ((response?.data?.upgrade?.failures ?? 0) === 0) {
        addToast({ color: 'success', title: 'Upgrade complete!' })
      } else {
        addToast({
          color: 'warning',
          title: 'Upgrade partially complete',
          text: (
            <EuiText size='xs' color='subdued'>
              One or more upgrade steps failed. You can safely retry.
            </EuiText>
          ),
        })
      }

      const latest = await api.setup_check()
      const upgrade = latest?.data?.upgrade || {}
      setIsUpgradeNeeded(Boolean(upgrade?.upgrade_needed))
      setUpgradeState(upgrade)
    } catch (e) {
      addToast(api.errorToast(e, { title: 'Failed to run upgrade' }))
    } finally {
      setIsUpgrading(false)
    }
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  if (isCheckingSetup)
    return <EuiProgress color='accent' position='fixed' size='s' />

  const renderConnectionFailurePrompt = () => (
    <EuiPanel paddingSize='xl'>
      <EuiProgress
        color='subdued'
        max={100}
        position='absolute'
        size="xs"
        value={100}
        valueText={false}
      />
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
    <EuiPanel paddingSize='xl'>
      <EuiProgress
        color='warning'
        max={100}
        position='absolute'
        size="xs"
        value={100}
        valueText={false}
      />
      <EuiIcon color="subdued" type="push" size="l" />
      <EuiSpacer size="l" />
      <EuiTitle size="m">
        <h3>Finish Setup</h3>
      </EuiTitle>
      <EuiSpacer size="l" />
      <EuiText size="s">
        <p>
          You're almost ready! Just click setup to finish.<br />
          This will create the <EuiCode style={{ padding: '0 2px' }} transparentBackground>esrs-*</EuiCode> index templates and indices.
        </p>
      </EuiText>
      <EuiSpacer size="l" />
      <EuiButton
        color='primary'
        disabled={isProcessing}
        fill
        isLoading={isProcessing}
        onClick={onSetup}
      >
        Setup
      </EuiButton>
    </EuiPanel>
  )

  const renderUpgradePrompt = () => (
    <EuiPanel paddingSize='xl'>
      <EuiProgress
        color='warning'
        max={100}
        position='absolute'
        size="xs"
        value={100}
        valueText={false}
      />
      <EuiIcon color="subdued" type="push" size="l" />
      <EuiSpacer size="l" />
      <EuiTitle size="m">
        <h2>Upgrade required</h2>
      </EuiTitle>
      <EuiSpacer size='l' />
      <EuiText style={{ textAlign: 'center' }}>
        <p>
          You must upgrade your indices to version <EuiCode>{upgradeState?.target_version || 'unknown'}</EuiCode> to match the server.<br />
          {upgradeState?.reindex_required
            ? 'This upgrade has breaking changes that require reindexing.'
            : 'This upgrade has no breaking changes.'}
        </p>
      </EuiText>
      <EuiSpacer size='xxl' />
      <EuiTitle size='xs'>
        <b>Pending changes</b>
      </EuiTitle>
      <EuiSpacer size='l' />
      {pendingSteps.length > 0 && (
        <EuiInMemoryTable
          compressed
          items={pendingSteps}
          itemId="_rowId"
          pagination={
            pendingSteps.length > 5
              ? { initialPageSize: 5, pageSizeOptions: [5, 10, 50], showPerPageOptions: true }
              : false
          }
          responsiveBreakpoint={false}
          tableLayout="auto"
          columns={[
            {
              field: 'version',
              name: 'Version',
              width: '75px',
              render: (version) => <EuiCode style={{ padding: 0 }} transparentBackground>{version}</EuiCode>,
            },
            {
              field: 'template',
              name: 'Index template',
              width: '150px',
              render: (template) => <EuiCode style={{ padding: 0 }} transparentBackground>{template}</EuiCode>,
            },
            {
              field: 'description',
              name: 'Change',
              render: (description) => description || '-',
            },
          ]}
          style={{ textAlign: 'left' }}
        />
      )}
      <EuiSpacer size='xl' />
      <div style={{ textAlign: 'center' }}>
        <EuiButton
          color='primary'
          fill
          disabled={isUpgrading}
          isLoading={isUpgrading}
          onClick={onUpgrade}
        >
          Upgrade
        </EuiButton>
      </div>
    </EuiPanel>
  )

  const renderWelcomePrompt = () => (
    <EuiPanel color='transparent' paddingSize='xl'>
      <EuiTitle size='l'>
        <h1 style={{ fontWeight: 700 }}>
          <big>Welcome!</big>
        </h1>
      </EuiTitle>
      <EuiSpacer size='l' />
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
      <EuiButton
        color='primary'
        iconType='globe'
        fill
        onClick={() => history.push('/workspaces')}
      >
        Go to workspaces
      </EuiButton>
    </EuiPanel>
  )

  return (
    <Page>
      <div style={{
        alignItems: 'center',
        display: 'flex',
        height: '100%',
        justifyContent: 'center',
        margin: '0 auto',
        textAlign: 'center',
        width: 600,
      }}>
        {hasCheckedSetup && !deploymentMode && renderConnectionFailurePrompt()}
        {hasCheckedSetup && deploymentMode && !isSetup && renderSetupPrompt()}
        {hasCheckedSetup && deploymentMode && isSetup && isUpgradeNeeded && renderUpgradePrompt()}
        {hasCheckedSetup && deploymentMode && isSetup && !isUpgradeNeeded && renderWelcomePrompt()}
      </div>
    </Page >
  )
}

export default Home