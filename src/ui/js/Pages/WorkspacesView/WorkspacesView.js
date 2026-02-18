/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useState } from 'react'
import {
  EuiButton,
  EuiButtonEmpty,
  EuiButtonIcon,
  EuiFlexGrid,
  EuiFlexGroup,
  EuiFlexItem,
  EuiHorizontalRule,
  EuiIcon,
  EuiMarkdownEditor,
  EuiMarkdownFormat,
  EuiPanel,
  EuiSpacer,
  EuiSkeletonTitle,
  EuiText,
  EuiToolTip,
  EuiTitle,
} from '@elastic/eui'
import {
  IconCodeDots,
  IconScale,
} from '@tabler/icons-react'
import { useAppContext } from '../../Contexts/AppContext'
import { usePageResources, useResources } from '../../Contexts/ResourceContext'
import { Page } from '../../Layout'
import api from '../../api'
import { getHistory } from '../../history'
import utils from '../../utils'

const WorkspacesView = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const history = getHistory()
  const { addToast } = useAppContext()
  const { workspace } = usePageResources()
  const { hasResources, setResource } = useResources()
  const isReady = hasResources(['workspace'])

  ////  State  /////////////////////////////////////////////////////////////////

  const [isEditingDescription, setIsEditingDescription] = useState(false)
  const [isProcessingDescription, setIsProcessingDescription] = useState(false)
  const [descriptionDraft, setDescriptionDraft] = useState('')

  ////  Effects  ///////////////////////////////////////////////////////////////

  useEffect(() => {
    setIsEditingDescription(false)
    setDescriptionDraft(workspace?.description || '')
  }, [workspace?._id, workspace?.description])

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onSaveDescription = async () => {
    if (!workspace?._id)
      return
    if (descriptionDraft == (workspace.description || '')) {
      setIsEditingDescription(false)
      return
    }
    let response
    try {
      setIsProcessingDescription(true)
      response = await api.workspaces_update(workspace._id, { description: descriptionDraft })
    } catch (e) {
      return addToast(api.errorToast(e, { title: 'Failed to update workspace description' }))
    } finally {
      setIsProcessingDescription(false)
    }
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    setResource('workspace', {
      ...workspace,
      description: descriptionDraft,
    })
    addToast(utils.toastDocCreateUpdateDelete('update', 'workspace', workspace._id))
    setIsEditingDescription(false)
  }

  const onCancelDescriptionEdit = () => {
    setDescriptionDraft(workspace?.description || '')
    setIsEditingDescription(false)
  }

  const doesDescriptionDraftDiffer = () => {
    return descriptionDraft != (workspace?.description || '')
  }

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
    <EuiPanel hasBorder={true} paddingSize='none' style={{ height: '100%' }}>

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

  const renderDescriptionPanel = () => (
    <EuiPanel color='transparent' paddingSize='m' style={{ height: '100%', minWidth: '400px' }}>
      <EuiFlexGroup alignItems='center' gutterSize='s' responsive={false}>
        <EuiFlexItem>
          <EuiTitle size='xs'>
            <h2>Workspace description</h2>
          </EuiTitle>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiToolTip content={isEditingDescription ? 'Cancel' : 'Edit'}>
            <EuiButtonIcon
              aria-label={isEditingDescription ? 'Cancel editing workspace description' : 'Edit workspace description'}
              color='text'
              display='base'
              iconType={isEditingDescription ? 'cross' : 'pencil'}
              onClick={() => {
                if (isEditingDescription)
                  onCancelDescriptionEdit()
                else
                  setIsEditingDescription(true)
              }}
              size='xs'
            />
          </EuiToolTip>
        </EuiFlexItem>
      </EuiFlexGroup>
      <EuiSpacer size='m' />
      {isEditingDescription && (
        <>
          <EuiMarkdownEditor
            aria-label='Workspace description editor'
            height={460}
            onChange={setDescriptionDraft}
            value={descriptionDraft}
          />
          <EuiSpacer size='m' />
          <EuiFlexGroup gutterSize='s' justifyContent='flexEnd' responsive={false}>
            <EuiFlexItem grow={false}>
              <EuiButtonEmpty
                isDisabled={isProcessingDescription}
                onClick={onCancelDescriptionEdit}
              >
                Cancel
              </EuiButtonEmpty>
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiButton
                fill
                isDisabled={isProcessingDescription || !doesDescriptionDraftDiffer()}
                isLoading={isProcessingDescription}
                onClick={onSaveDescription}
              >
                Save description
              </EuiButton>
            </EuiFlexItem>
          </EuiFlexGroup>
        </>
      )}
      {!isEditingDescription && !workspace?.description?.trim() && (
        <>
          <EuiText color='subdued' size='s'>
            Add project goals, content context, and collaboration guidance for humans and AI agents.
          </EuiText>
          <EuiSpacer size='m' />
          <EuiButtonEmpty flush='left' iconType='pencil' onClick={() => setIsEditingDescription(true)}>
            Add description
          </EuiButtonEmpty>
        </>
      )}
      {!isEditingDescription && !!workspace?.description?.trim() && (
        <EuiMarkdownFormat>{workspace.description}</EuiMarkdownFormat>
      )}
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
    <Page title={
      <EuiSkeletonTitle isLoading={!isReady} size='l'>
        {!workspace?.name &&
          <>Not found</>
        }
        {!!workspace?.name &&
          <>{workspace.name}</>
        }
      </EuiSkeletonTitle>
    } buttons={[ renderButtonDisplays() ]}>
      <EuiFlexGroup alignItems='stretch' gutterSize='m' responsive={true}>
        <EuiFlexItem grow={1}>
          {renderDescriptionPanel()}
        </EuiFlexItem>
        <EuiFlexItem grow={2}>
          <EuiFlexGrid columns={1} gutterSize='m'>
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
        </EuiFlexItem>
      </EuiFlexGroup>
    </Page>
  )
}

export default WorkspacesView