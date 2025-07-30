/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License;
 * you may not use this file except in compliance with the Elastic License.
 */

import {
  EuiButton,
  EuiButtonIcon,
  EuiFlexGrid,
  EuiFlexGroup,
  EuiFlexItem,
  EuiHorizontalRule,
  EuiIcon,
  EuiPanel,
  EuiSkeletonTitle,
  EuiText,
  EuiTitle,
} from '@elastic/eui'
import {
  IconCodeDots,
  IconScale,
} from '@tabler/icons-react'
import { usePageResources, useResources } from '../../Contexts/ResourceContext'
import { Page } from '../../Layout'
import { getHistory } from '../../history'

const WorkspacesView = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const history = getHistory()
  const { workspace } = usePageResources()
  const isReady = useResources().hasResources(['workspace'])

  const renderScenarios = () => (
    <>
      <EuiButton onClick={() => {
        history.push(`/workspaces/${workspace._id}/scenarios`)
      }}>
        Manage scenarios
      </EuiButton>
    </>
  )

  const renderJudgements = () => (
    <>
      <EuiButton onClick={() => {
        history.push(`/workspaces/${workspace._id}/judgements`)
      }}>
        Manage judgements
      </EuiButton>
    </>
  )

  const renderStrategies = () => (
    <>
      <EuiButton onClick={() => {
        history.push(`/workspaces/${workspace._id}/strategies`)
      }}>
        Manage strategies
      </EuiButton>
    </>
  )

  const renderBenchmarks = () => (
    <>
      <EuiButton onClick={() => {
        history.push(`/workspaces/${workspace._id}/benchmarks`)
      }}>
        Manage benchmarks
      </EuiButton>
    </>
  )

  const renderIcon = (assetType) => {
    if (assetType == 'scenarios')
      return (
        <div style={{ marginTop: '3px' }}>
          <EuiIcon color='subdued' type='comment' size='m' />
        </div>
      )
    else if (assetType == 'judgements')
      return (
        <div style={{ marginTop: '2px' }}>
          <EuiText color='subdued' component='span'><IconScale stroke={1.5} size={18} /></EuiText>
        </div>
      )
    else if (assetType == 'strategies')
      return (
        <div style={{ marginTop: '2px' }}>
          <EuiText color='subdued' component='span'><IconCodeDots stroke={1.5} size={20} /></EuiText>
        </div>
      )
    else if (assetType == 'benchmarks')
      return (
        <div style={{ marginTop: '2px' }}>
          <EuiIcon color='subdued' type='stats' size='m' />
        </div>
      )
  }

  const renderPanel = (title, assetType, children) => (
    <EuiPanel paddingSize='none'>

      {/* Header */}
      <EuiPanel color='transparent'>
        <EuiFlexGroup>
          <EuiFlexItem grow>
            <EuiFlexGroup gutterSize='m'>
              <EuiFlexItem grow={false}>
                <div style={{ height: '16px' }}>
                  {renderIcon(assetType)}
                </div>
              </EuiFlexItem>
              <EuiFlexItem grow>
                <EuiTitle size='xs'>
                  <h2>{title}</h2>
                </EuiTitle>
              </EuiFlexItem>
            </EuiFlexGroup>
          </EuiFlexItem>
          <EuiFlexItem grow={false}>
            <EuiButtonIcon
              aria-label='Manage'
              color='text'
              display='base'
              iconSize='s'
              iconType='doubleArrowRight'
              onClick={() => {
                history.push(`/workspaces/${workspace._id}/${assetType}`)
              }}
              size='xs'
            />
          </EuiFlexItem>
        </EuiFlexGroup>
      </EuiPanel>
      <EuiHorizontalRule margin='none' />

      {/* Content */}
      <EuiPanel color='transparent'>
        {children}
      </EuiPanel>
    </EuiPanel>
  )

  const renderButtonDisplays = () => (
    <EuiButton iconType='palette' onClick={() => {
        history.push(`/workspaces/${workspace._id}/displays`)
      }}>
      Manage displays
    </EuiButton>
  )

  return (
    <Page panelled title={
      <EuiSkeletonTitle isLoading={!isReady} size='l'>
        {!workspace?.name &&
          <>Not found</>
        }
        {!!workspace?.name &&
          <>{workspace.name}</>
        }
      </EuiSkeletonTitle>
    } buttons={[ renderButtonDisplays() ]}>
      <EuiFlexGrid columns={4} gutterSize='m'>
        <EuiFlexItem>
          {renderPanel('Scenarios', 'scenarios', renderScenarios())}
        </EuiFlexItem>
        <EuiFlexItem>
          {renderPanel('Judgements', 'judgements', renderJudgements())}
        </EuiFlexItem>
        <EuiFlexItem>
          {renderPanel('Strategies', 'strategies', renderStrategies())}
        </EuiFlexItem>
        <EuiFlexItem>
          {renderPanel('Benchmarks', 'benchmarks', renderBenchmarks())}
        </EuiFlexItem>
      </EuiFlexGrid>
    </Page>
  )
}

export default WorkspacesView