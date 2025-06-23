import React from 'react'
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

const FlyoutRuntime = ({ runtime, onClose }) => {

  // Runtime assets as arrays for table components.
  const indices = Object.entries(runtime.indices || {})
    .map(([key, value]) => ({ _id: key, ...value }))
  const strategies = Object.entries(runtime.strategies || {})
    .map(([key, value]) => ({ _id: key, ...value }))
  const scenarios = Object.entries(runtime.scenarios || {})
    .map(([key, value]) => ({ _id: key, ...value }))
  const judgements = Object.entries(runtime.judgements || {})
    .map(([key, value]) => ({ _id: key, ...value, scenario: runtime.scenarios?.[value.scenario_id]?.name }))

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
    <EuiFlyout hideCloseButton onClose={onClose} ownFocus size='m'>
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