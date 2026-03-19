/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useRouteMatch } from 'react-router-dom'
import {
  EuiButtonIcon,
  EuiHorizontalRule,
  EuiIcon,
  EuiPanel,
  EuiSpacer,
  EuiText,
  EuiToolTip,
} from '@elastic/eui'
import {
  IconCodeDots,
  IconScale,
} from '@tabler/icons-react'
import { useAppContext } from '../Contexts/AppContext'
import { usePageResources } from '../Contexts/ResourceContext'

const SideNav = () => {

  const path = useRouteMatch().path

  ////  Context  ///////////////////////////////////////////////////////////////

  const { darkMode, setSidebarOpen, sidebarOpen } = useAppContext()

  // Do this in case the sidebar is on a page that isn't in ResourceProvider
  const useSafePageResources = () => {
    try {
      return usePageResources()
    } catch (error) {
      return {}
    }
  }
  const { workspace } = useSafePageResources()

  ////  Render  ////////////////////////////////////////////////////////////////

  return (
    <EuiPanel
      color='transparent'
      paddingSize='s'
      style={{
        borderRadius: 0,
        height: '100%',
        textAlign: 'center',
        zIndex: 99
      }}
    >

      <EuiToolTip content='Workspaces' position='right'>
        <a href={`#/workspaces`} style={{ color: 'inherit' }}>
          <EuiButtonIcon
            aria-label='Workspaces'
            display={path === '/workspaces' ? 'base' : 'empty'}
            color={path === '/workspaces' ? 'primary' : 'text'}
            iconType='globe'
            size='s'
          />
          {sidebarOpen &&
            <EuiText color='text' size='xs' style={{ fontWeight: 500, marginTop: '4px' }}>
              Workspaces
            </EuiText>
          }
        </a>
      </EuiToolTip>

      {workspace?._id &&
        <>
          <EuiHorizontalRule margin='s' style={{ marginTop: '6px' }} />

          <EuiToolTip content={sidebarOpen ? undefined : 'Workspace'} position='right'>
            <a href={`#/workspaces/${workspace._id}`} style={{ color: 'inherit' }}>
              <EuiButtonIcon
                aria-label='Workspace'
                display={path === '/workspaces/:workspace_id' ? 'base' : 'empty'}
                color={path === '/workspaces/:workspace_id' ? 'primary' : 'text'}
                iconType='home'
                size='s'
              />
              {sidebarOpen &&
                <EuiText color='text' size='xs' style={{ fontWeight: 500, marginTop: '4px' }}>
                  Workspace
                </EuiText>
              }
            </a>
          </EuiToolTip>

          <EuiSpacer size={sidebarOpen ? 'm' : 'xs'} />

          <EuiToolTip content={sidebarOpen ? undefined : 'Displays'} position='right'>
            <a href={`#/workspaces/${workspace._id}/displays`} style={{ color: 'inherit' }}>
              <EuiButtonIcon
                aria-label='Displays'
                display={path.startsWith('/workspaces/:workspace_id/displays') ? 'base' : 'empty'}
                color={path.startsWith('/workspaces/:workspace_id/displays') ? 'primary' : 'text'}
                iconType='palette'
                size='s'
              />
              {sidebarOpen &&
                <EuiText color='text' size='xs' style={{ fontWeight: 500, marginTop: '4px' }}>
                  Displays
                </EuiText>
              }
            </a>
          </EuiToolTip>

          <EuiSpacer size={sidebarOpen ? 'm' : 'xs'} />

          <EuiToolTip content={sidebarOpen ? undefined : 'Scenarios'} position='right'>
            <a href={`#/workspaces/${workspace._id}/scenarios`} style={{ color: 'inherit' }}>
              <EuiButtonIcon
                aria-label='Scenarios'
                display={path.startsWith('/workspaces/:workspace_id/scenarios') ? 'base' : 'empty'}
                color={path.startsWith('/workspaces/:workspace_id/scenarios') ? 'primary' : 'text'}
                iconType='comment'
                size='s'
              />
              {sidebarOpen &&
                <EuiText color='text' size='xs' style={{ fontWeight: 500, marginTop: '4px' }}>
                  Scenarios
                </EuiText>
              }
            </a>
          </EuiToolTip>

          <EuiSpacer size={sidebarOpen ? 'm' : 'xs'} />

          <EuiToolTip content={sidebarOpen ? undefined : 'Judgements'} position='right'>
            <a href={`#/workspaces/${workspace._id}/judgements`} style={{ color: 'inherit' }}>
              <EuiButtonIcon
                aria-label='Judgements'
                display={path.startsWith('/workspaces/:workspace_id/judgements') ? 'base' : 'empty'}
                color={path.startsWith('/workspaces/:workspace_id/judgements') ? 'primary' : 'text'}
                iconType={() => (
                  <EuiText color='text' style={{ marginBottom: '-4px' }}>
                    <IconScale stroke={1.5} size={16} />
                  </EuiText>
                )}
                size='s'
              />
              {sidebarOpen &&
                <EuiText color='text' size='xs' style={{ fontWeight: 500, marginTop: '4px' }}>
                  Judgements
                </EuiText>
              }
            </a>
          </EuiToolTip>

          <EuiSpacer size={sidebarOpen ? 'm' : 'xs'} />

          <EuiToolTip content={sidebarOpen ? undefined : 'Strategies'} position='right'>
            <a href={`#/workspaces/${workspace._id}/strategies`} style={{ color: 'inherit' }}>
              <EuiButtonIcon
                aria-label='Strategies'
                display={path.startsWith('/workspaces/:workspace_id/strategies') ? 'base' : 'empty'}
                color={path.startsWith('/workspaces/:workspace_id/strategies') ? 'primary' : 'text'}
                iconType={() => (
                  <EuiText color='text' style={{ marginBottom: '-4px' }}>
                    <IconCodeDots stroke={1.5} size={16} />
                  </EuiText>
                )}
                size='s'
              />
              {sidebarOpen &&
                <EuiText color='text' size='xs' style={{ fontWeight: 500, marginTop: '4px' }}>
                  Strategies
                </EuiText>
              }
            </a>
          </EuiToolTip>

          <EuiSpacer size={sidebarOpen ? 'm' : 'xs'} />

          <EuiToolTip content={sidebarOpen ? undefined : 'Benchmarks'} position='right'>
            <a href={`#/workspaces/${workspace._id}/benchmarks`} style={{ color: 'inherit' }}>
              <EuiButtonIcon
                aria-label='Benchmarks'
                display={path.startsWith('/workspaces/:workspace_id/benchmarks') ? 'base' : 'empty'}
                color={path.startsWith('/workspaces/:workspace_id/benchmarks') ? 'primary' : 'text'}
                iconType='stats'
                size='s'
              />
              {sidebarOpen &&
                <EuiText color='text' size='xs' style={{ fontWeight: 500, marginTop: '4px' }}>
                  Benchmarks
                </EuiText>
              }
            </a>
          </EuiToolTip>
        </>
      }

      <div style={{
        position: 'absolute',
        bottom: '8px',
        left: '8px',
        right: '8px'
      }}>
        <EuiHorizontalRule margin='s' />

        <EuiToolTip content={sidebarOpen ? 'Close sidebar' : 'Open sidebar'} position='right'>
          <EuiButtonIcon
            aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            color='text'
            iconType={sidebarOpen ? 'transitionLeftOut' : 'transitionLeftIn'}
            onClick={() => setSidebarOpen(!sidebarOpen)}
            size='s'
          />
        </EuiToolTip>
      </div>
    </EuiPanel>
  )
}

export default SideNav