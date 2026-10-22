/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  EuiButtonEmpty,
  EuiFlyout,
  EuiFlyoutBody,
  EuiFlyoutFooter,
  EuiFlyoutHeader,
  EuiNotificationBadge,
  EuiSpacer,
  EuiTabbedContent,
  EuiTitle,
} from '@elastic/eui'
import TableRuntimeIndices from './TableRuntimeIndices'
import TableRuntimeJudgements from './TableRuntimeJudgements'
import TableRuntimeScenarios from './TableRuntimeScenarios'
import TableRuntimeStrategies from './TableRuntimeStrategies'

const FlyoutRuntime = ({ runtime, isLoading, onClose }) => {

  // Runtime assets are loaded on demand from the forensics store, so `runtime`
  // may be undefined while loading or for runs that have no forensics.
  const rt = runtime || {}

  // Runtime assets as arrays for table components.
  const indices = Object.entries(rt.indices || {})
    .map(([key, value]) => ({ _id: key, ...value }))
  const strategies = Object.entries(rt.strategies || {})
    .map(([key, value]) => ({ _id: key, ...value }))
  const scenarios = Object.entries(rt.scenarios || {})
    .map(([key, value]) => ({ _id: key, ...value }))
  const judgements = Object.entries(rt.judgements || {})
    .map(([key, value]) => ({ _id: key, ...value, scenario: rt.scenarios?.[value.scenario_id]?.name }))

  const renderIndices = () => {
    return (<>
      <EuiSpacer size='l' />
      <TableRuntimeIndices items={indices} />
    </>)
  }

  const renderStrategies = () => {
    return (<>
      <EuiSpacer size='l' />
      <TableRuntimeStrategies items={strategies} />
    </>)
  }

  const renderScenarios = () => {
    return (<>
      <EuiSpacer size='l' />
      <TableRuntimeScenarios items={scenarios} />
    </>)
  }

  const renderJudgements = () => {
    return (<>
      <EuiSpacer size='l' />
      <TableRuntimeJudgements items={judgements} />
    </>)
  }

  const renderBadgeCount = (assetType) => {
    return (
      <EuiNotificationBadge color='subdued' style={{ marginLeft: '8px' }}>
        <small>{Object.keys(runtime[assetType] || []).length || 0}</small>
      </EuiNotificationBadge>
    )
  }

  return (
    <EuiFlyout hideCloseButton onClose={onClose} ownFocus size='l'>
      <EuiFlyoutHeader>
        <EuiTitle size='m'>
          <h2>Runtime assets</h2>
        </EuiTitle>
      </EuiFlyoutHeader>
      <EuiFlyoutBody>
        <EuiTabbedContent
          tabs={[
            {
              id: 'indices',
              name: (
                <div>
                  Indices {renderBadgeCount('indices')}
                </div>
              ),
              content: renderIndices()
            },
            {
              id: 'strategies',
              name: (
                <div>
                  Strategies {renderBadgeCount('strategies')}
                </div>
              ),
              content: renderStrategies()
            },
            {
              id: 'scenarios',
              name: (
                <div>
                  Scenarios {renderBadgeCount('scenarios')}
                </div>
              ),
              content: renderScenarios()
            },
            {
              id: 'judgements',
              name: (
                <div>
                  Judgements {renderBadgeCount('judgements')}
                </div>
              ),
              content: renderJudgements()
            }
          ]}
        />
      </EuiFlyoutBody>
      <EuiFlyoutFooter>
        <EuiButtonEmpty flush='left' iconType='cross' onClick={onClose}>
          Close
        </EuiButtonEmpty>
      </EuiFlyoutFooter>
    </EuiFlyout>
  )
}

export default FlyoutRuntime