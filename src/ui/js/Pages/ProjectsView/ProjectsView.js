import { useEffect, useState } from 'react'
import {
  EuiButtonIcon,
  EuiFlexGrid,
  EuiFlexGroup,
  EuiFlexItem,
  EuiHorizontalRule,
  EuiPanel,
  EuiSkeletonTitle,
  EuiTitle,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { usePageResources, useResources } from '../../Contexts/ResourceContext'
import { Page } from '../../Layout'
import api from '../../api'
import utils from '../../utils'

const ProjectsView = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const { project } = usePageResources()
  const isReady = useResources().hasResources(['project'])

  const renderScenarios = () => (
    <>test</>
  )

  const renderJudgements = () => (
    <>test</>
  )

  const renderStrategies = () => (
    <>test</>
  )

  const renderBenchmarks = () => (
    <>test</>
  )

  const renderPanel = (title, children) => (
    <EuiPanel paddingSize='none'>

      {/* Header */}
      <EuiPanel color='transparent'>
        <EuiFlexGroup>
          <EuiFlexItem grow>
            <EuiTitle size='xs'>
              <h2>{title}</h2>
            </EuiTitle>
          </EuiFlexItem>
          <EuiFlexItem grow={false}>
            <EuiButtonIcon
              aria-label='Manage'
              color='primary'
              display='base'
              iconSize='s'
              iconType='gear'
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

  return (
    <Page panelled title={
      <EuiSkeletonTitle isLoading={!isReady} size='l'>
        {!project?.name &&
          <>Not found</>
        }
        {!!project?.name &&
          <>{project.name}</>
        }
      </EuiSkeletonTitle>
    }>
      <EuiFlexGrid columns={4} gutterSize='m'>
        <EuiFlexItem>
          {renderPanel('Scenarios', renderScenarios())}
        </EuiFlexItem>
        <EuiFlexItem>
          {renderPanel('Judgements', renderJudgements())}
        </EuiFlexItem>
        <EuiFlexItem>
          {renderPanel('Strategies', renderStrategies())}
        </EuiFlexItem>
        <EuiFlexItem>
          {renderPanel('Benchmarks', renderBenchmarks())}
        </EuiFlexItem>
      </EuiFlexGrid>
    </Page>
  )
}

export default ProjectsView