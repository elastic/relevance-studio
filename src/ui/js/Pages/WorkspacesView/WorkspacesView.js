/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
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
  const [descriptionEditorHeight, setDescriptionEditorHeight] = useState(320)
  const descriptionEditContainerRef = useRef(null)
  const descriptionEditActionsRef = useRef(null)

  ////  Effects  ///////////////////////////////////////////////////////////////

  useEffect(() => {
    setIsEditingDescription(false)
    setDescriptionDraft(workspace?.description || '')
  }, [workspace?._id, workspace?.description])

  useLayoutEffect(() => {
    if (!isEditingDescription)
      return

    const setEditorHeight = () => {
      const containerHeight = descriptionEditContainerRef.current?.clientHeight || 0
      const actionsHeight = descriptionEditActionsRef.current?.offsetHeight || 0
      const spacerHeight = 16
      const nextHeight = Math.max(180, containerHeight - actionsHeight - spacerHeight)
      setDescriptionEditorHeight(nextHeight)
    }

    setEditorHeight()

    let resizeObserver
    if (window.ResizeObserver && descriptionEditContainerRef.current) {
      resizeObserver = new window.ResizeObserver(setEditorHeight)
      resizeObserver.observe(descriptionEditContainerRef.current)
    } else {
      window.addEventListener('resize', setEditorHeight)
    }

    return () => {
      if (resizeObserver)
        resizeObserver.disconnect()
      else
        window.removeEventListener('resize', setEditorHeight)
    }
  }, [isEditingDescription])

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
        <EuiFlexGroup responsive={false}>
          <EuiFlexItem grow>
            <EuiFlexGroup gutterSize='m' responsive={false}>
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
    <EuiPanel
      hasBorder={false}
      color='transparent'
      paddingSize='none'
      style={{
        display: 'flex',
        flex: 1,
        flexDirection: 'column',
        height: '100%',
        minHeight: 0,
        overflow: 'hidden',
      }}
    >
      <div style={{ flexShrink: 0, padding: '16px 0' }}>
        <EuiFlexGroup alignItems='center' responsive={false}>
          <EuiFlexItem grow>
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
                iconSize='m'
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
      </div>
      <EuiHorizontalRule margin='none' />
      <div
        style={{
          display: 'flex',
          flex: 1,
          flexDirection: 'column',
          minHeight: 0,
          overflowY: isEditingDescription ? 'hidden' : 'auto',
          padding: '16px 0',
        }}
      >
        {isEditingDescription && (
          <div ref={descriptionEditContainerRef} style={{ display: 'flex', flex: 1, flexDirection: 'column', minHeight: 0 }}>
            <div style={{ flex: 1, minHeight: 0 }}>
              <EuiMarkdownEditor
                aria-label='Workspace description editor'
                height={descriptionEditorHeight}
                onChange={setDescriptionDraft}
                value={descriptionDraft}
              />
            </div>
            <EuiSpacer size='m' />
            <div ref={descriptionEditActionsRef} style={{ flexShrink: 0 }}>
              <EuiFlexGroup
                gutterSize='s'
                justifyContent='flexEnd'
                responsive={false}
              >
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
            </div>
          </div>
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
          <EuiMarkdownFormat>{workspace.description.trimStart()}</EuiMarkdownFormat>
        )}
      </div>
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
      <div style={{ display: 'flex', flex: 1, gap: '16px', height: '100%', minHeight: 0, overflow: 'hidden' }}>
        <div style={{ display: 'flex', flex: 1, minHeight: 0, minWidth: '400px', overflow: 'hidden' }}>
          {renderDescriptionPanel()}
        </div>
        <div style={{ display: 'flex', flex: 2, minHeight: 0, overflow: 'hidden' }}>
          <EuiPanel
            color='transparent'
            hasBorder={false}
            hasShadow={false}
            paddingSize='none'
            style={{ display: 'flex', flex: 1, minHeight: 0, overflowY: 'auto' }}
          >
            <EuiFlexGrid columns={1} gutterSize='m' style={{ flex: 1, minHeight: 'max-content' }}>
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
          </EuiPanel>
        </div>
      </div>
    </Page>
  )
}

export default WorkspacesView