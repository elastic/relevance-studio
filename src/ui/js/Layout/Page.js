/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useState } from 'react'
import { useRouteMatch } from 'react-router-dom'
import {
  EuiButton,
  EuiButtonIcon,
  EuiFlexGroup,
  EuiFlexItem,
  EuiHeader,
  EuiIcon,
  EuiLink,
  EuiPageTemplate,
  EuiPanel,
  EuiPopover,
  EuiPopoverTitle,
  EuiSpacer,
  EuiText,
  EuiToolTip,
} from '@elastic/eui'
import { useAppContext } from '../Contexts/AppContext'
import { useChatContext } from '../Contexts/ChatContext'
import Breadcrumbs from './Breadcrumbs'
import SideNav from './SideNav'

const Page = ({ title, buttons, paddingSize = 's', children, }) => {

  ////  State  /////////////////////////////////////////////////////////////////

  const [isHelpPopoverOpen, setIsHelpPopoverOpen] = useState(false)
  const [isInfoPopoverOpen, setIsInfoPopoverOpen] = useState(false)

  ////  Context  ///////////////////////////////////////////////////////////////

  const {
    darkMode,
    deploymentMode,
    licenseStatus,
    licenseType,
    sidebarOpen,
    setDarkMode,
  } = useAppContext()

  const {
    chatOpen,
    setChatOpen,
  } = useChatContext()

  const path = useRouteMatch().path

  const closeHelpPopover = () => setIsHelpPopoverOpen(false)
  const closeInfoPopover = () => setIsInfoPopoverOpen(false)

  const headerSections = [
    {
      items: [
        <a href='#/' style={{ color: 'inherit' }}>
          <div style={{ height: '48px', textAlign: 'center', width: '48px' }}>
            <EuiButtonIcon
              aria-label='Elasticsearch Relevance Studio'
              iconType={() => (
                <EuiIcon
                  type={
                    darkMode
                      ? 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzMiIgaGVpZ2h0PSIzMiIgdmlld0JveD0iMCAwIDMyIDMyIiBmaWxsPSJub25lIj4KICA8IS0tIFRlYWwgc2hhcGUgLS0+CiAgPHBhdGggZmlsbC1ydWxlPSJldmVub2RkIiBjbGlwLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik01LjIzNjM5IDE4LjI1OTZDNS4yMzYzOSAyMC44NDA2IDYuMDU1NjcgMjMuMjM0NCA3LjQ0ODQxIDI1LjE5NTRMMTUuNjIxNiAxMy41OTkzTDIwLjY3MzEgMTguMDE2N0wyNi4yNjY4IDEwLjI2MzFDMjQuMDU5NiA3Ljc5MzYgMjAuODQ4OCA2LjIzNjM2IDE3LjI4IDYuMjM2MzZDMTAuNjM4MyA2LjIzNjM2IDUuMjM2MzkgMTEuNjI5OCA1LjIzNjM5IDE4LjI1OTZaTTE2LjAyNDggMTguMDE2N0w5LjQ1MjA0IDI3LjM4OEMxMS41NTg2IDI5LjE5MDMgMTQuMjk0IDMwLjI4MDQgMTcuMjggMzAuMjgwNEMyMC4wMjIgMzAuMjgwNCAyMi41NTI2IDI5LjM2MTEgMjQuNTc5MSAyNy44MTUzTDI4LjYwMTkgMzEuMjU0NUwzMiAyNy40NzQ3TDI3Ljg4MzkgMjMuOTU1QzI4LjgwMjEgMjIuMjU4OSAyOS4zMjM2IDIwLjMxODggMjkuMzIzNiAxOC4yNTk2QzI5LjMyMzYgMTYuMzAyOSAyOC44NTMgMTQuNDUzOCAyOC4wMTg5IDEyLjgxOTRMMjEuMDY4NiAyMi40MzY5TDE2LjAyNDggMTguMDE2N1oiIGZpbGw9IiMwMkJDQjciLz4KCiAgPCEtLSBZZWxsb3cgYmFja2dyb3VuZCAtLT4KICA8cGF0aCBkPSJNMzAuNzE3OCA0LjA5MzM3TDIwLjY3MzEgMTguMDE2N0wxNS42MjE2IDEzLjU5OTNMMy4yMzgxMyAzMS4xNjlDMS4zODkxNCAzMC43ODM5IDAgMjkuMTQ1MSAwIDI3LjE4MThWNS4wNzI3M0MwIDIuODIzNDIgMS44MjM0MiAxIDQuMDcyNzMgMUgyNi43NjM2QzI4LjY3NTMgMSAzMC4yNzk0IDIuMzE3MTEgMzAuNzE3OCA0LjA5MzM3WiIgZmlsbD0iI0ZFQzUxNCIvPgoKICA8IS0tIEdBUDogZHVwbGljYXRlZCB3aGl0ZSBzaGFwZSB3aXRoIDRweCBzdHJva2UgbWF0Y2hpbmcgYmFja2dyb3VuZCAtLT4KICA8cGF0aAogICAgZD0iTTcuNDQ4NDEgMjUuMTk1NEM2LjA1NTY3IDIzLjIzNDQgNS4yMzYzOSAyMC44NDA2IDUuMjM2MzkgMTguMjU5NkM1LjIzNjM5IDExLjYyOTggMTAuNjM4MyA2LjIzNjM2IDE3LjI4IDYuMjM2MzZDMjAuODQ4OCA2LjIzNjM2IDI0LjA1OTYgNy43OTM2IDI2LjI2NjggMTAuMjYzMUwyMC42NzMxIDE4LjAxNjdMMTUuNjIxNiAxMy41OTkzTDcuNDQ4NDEgMjUuMTk1NFoiCiAgICBmaWxsPSJub25lIgogICAgc3Ryb2tlPSJyZ2IoMTEsMjIsNDApIgogICAgc3Ryb2tlLXdpZHRoPSI0IgogIC8+CgogIDwhLS0gRm9yZWdyb3VuZCB3aGl0ZSBzaGFwZSAtLT4KICA8cGF0aAogICAgZD0iTTcuNDQ4NDEgMjUuMTk1NEM2LjA1NTY3IDIzLjIzNDQgNS4yMzYzOSAyMC44NDA2IDUuMjM2MzkgMTguMjU5NkM1LjIzNjM5IDExLjYyOTggMTAuNjM4MyA2LjIzNjM2IDE3LjI4IDYuMjM2MzZDMjAuODQ4OCA2LjIzNjM2IDI0LjA1OTYgNy43OTM2IDI2LjI2NjggMTAuMjYzMUwyMC42NzMxIDE4LjAxNjdMMTUuNjIxNiAxMy41OTkzTDcuNDQ4NDEgMjUuMTk1NFoiCiAgICBmaWxsPSIjRkZGRkZGIgogIC8+Cjwvc3ZnPgo='
                      : 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZmlsbC1ydWxlPSJldmVub2RkIiBjbGlwLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik01LjIzNjM5IDE4LjI1OTZDNS4yMzYzOSAyMC44NDA2IDYuMDU1NjcgMjMuMjM0NCA3LjQ0ODQxIDI1LjE5NTRMMTUuNjIxNiAxMy41OTkzTDIwLjY3MzEgMTguMDE2N0wyNi4yNjY4IDEwLjI2MzFDMjQuMDU5NiA3Ljc5MzYgMjAuODQ4OCA2LjIzNjM2IDE3LjI4IDYuMjM2MzZDMTAuNjM4MyA2LjIzNjM2IDUuMjM2MzkgMTEuNjI5OCA1LjIzNjM5IDE4LjI1OTZaTTE2LjAyNDggMTguMDE2N0w5LjQ1MjA0IDI3LjM4OEMxMS41NTg2IDI5LjE5MDMgMTQuMjk0IDMwLjI4MDQgMTcuMjggMzAuMjgwNEMyMC4wMjIgMzAuMjgwNCAyMi41NTI2IDI5LjM2MTEgMjQuNTc5MSAyNy44MTUzTDI4LjYwMTkgMzEuMjU0NUwzMiAyNy40NzQ3TDI3Ljg4MzkgMjMuOTU1QzI4LjgwMjEgMjIuMjU4OSAyOS4zMjM2IDIwLjMxODggMjkuMzIzNiAxOC4yNTk2QzI5LjMyMzYgMTYuMzAyOSAyOC44NTMgMTQuNDUzOCAyOC4wMTg5IDEyLjgxOTRMMjEuMDY4NiAyMi40MzY5TDE2LjAyNDggMTguMDE2N1oiIGZpbGw9IiMwMkJDQjciLz4KPHBhdGggZD0iTTMwLjcxNzggNC4wOTMzN0wyMC42NzMxIDE4LjAxNjdMMTUuNjIxNiAxMy41OTkzTDMuMjM4MTMgMzEuMTY5QzEuMzg5MTQgMzAuNzgzOSAwIDI5LjE0NTEgMCAyNy4xODE4VjUuMDcyNzNDMCAyLjgyMzQyIDEuODIzNDIgMSA0LjA3MjczIDFIMjYuNzYzNkMyOC42NzUzIDEgMzAuMjc5NCAyLjMxNzExIDMwLjcxNzggNC4wOTMzN1oiIGZpbGw9IiNGRUM1MTQiLz4KPHBhdGggZD0iTTcuNDQ4NDEgMjUuMTk1NEM2LjA1NTY3IDIzLjIzNDQgNS4yMzYzOSAyMC44NDA2IDUuMjM2MzkgMTguMjU5NkM1LjIzNjM5IDExLjYyOTggMTAuNjM4MyA2LjIzNjM2IDE3LjI4IDYuMjM2MzZDMjAuODQ4OCA2LjIzNjM2IDI0LjA1OTYgNy43OTM2IDI2LjI2NjggMTAuMjYzMUwyMC42NzMxIDE4LjAxNjdMMTUuNjIxNiAxMy41OTkzTDcuNDQ4NDEgMjUuMTk1NFoiIGZpbGw9IiMzNDM3NDEiLz4KPC9zdmc+Cg=='
                  }
                  style={{
                    height: '24px',
                    width: '24px'
                  }}
                />
              )}
              style={{ height: '37px', margin: '6px', width: '35px' }}
            />
          </div>
        </a>,
        <div style={{ paddingLeft: '8px' }}>
          {
            path === '/'
              ? <EuiText size='s' style={{ fontWeight: 500 }}>Elasticsearch Relevance Studio</EuiText>
              : <Breadcrumbs />
          }
        </div>,
      ],
    },
    {
      items: [
        <EuiToolTip content={`Switch to ${darkMode ? 'light' : 'dark'} mode`}>
          <EuiButtonIcon
            aria-label={`Switch to ${darkMode ? 'light' : 'dark'} mode`}
            color="text"
            iconType={darkMode ? 'sun' : 'moon'}
            onClick={() => setDarkMode(!darkMode)}
            style={{ height: '38px', marginLeft: '6px', width: '38px' }}
          />
        </EuiToolTip>,
        <EuiPopover
          anchorPosition="downCenter"
          button={
            <EuiToolTip content='Help'>
              <EuiButtonIcon
                aria-label="Help"
                color="text"
                iconType="question"
                onClick={() => setIsHelpPopoverOpen(!isHelpPopoverOpen)}
                style={{ height: '38px', marginLeft: '6px', width: '38px' }}
              />
            </EuiToolTip>
          }
          isOpen={isHelpPopoverOpen}
          closePopover={closeHelpPopover}
        >
          <>
            <EuiPopoverTitle>Help</EuiPopoverTitle>
            <EuiLink href='https://elastic.github.io/relevance-studio/' target='_blank' external={false}>
              <EuiText size="s" style={{ fontWeight: 500 }}>
                Documentation
              </EuiText>
            </EuiLink>
            <EuiSpacer size="m" />
            <EuiLink href='https://github.com/elastic/relevance-studio' target='_blank' external={false}>
              <EuiText size="s" style={{ fontWeight: 500 }}>
                GitHub
              </EuiText>
            </EuiLink>
          </>
        </EuiPopover>,
        <EuiPopover
          anchorPosition="downCenter"
          button={
            <EuiToolTip content='Deployment info'>
              <EuiButtonIcon
                aria-label='Deployment info'
                iconType="logoElastic"
                onClick={() => setIsInfoPopoverOpen(!isInfoPopoverOpen)}
                style={{ height: '38px', marginLeft: '6px', width: '38px' }}
              />
            </EuiToolTip>
          }
          isOpen={isInfoPopoverOpen}
          closePopover={closeInfoPopover}
        >
          <>
            <EuiPopoverTitle>Studio Deployment Info</EuiPopoverTitle>
            <EuiFlexGroup alignItems="center">
              <EuiFlexItem grow={false}>
                {!deploymentMode && <EuiIcon size="s" type="question" />}
                {deploymentMode === 'serverless' && <EuiIcon size="s" type="logoCloud" />}
                {deploymentMode === 'cloud' && <EuiIcon size="s" type="logoCloud" />}
                {deploymentMode === 'standard' && <EuiIcon size="s" type="logoElasticsearch" />}
              </EuiFlexItem>
              <EuiFlexItem grow={true}>
                <EuiText size="s">
                  {!deploymentMode && "Unknown"}
                  {deploymentMode === 'serverless' && "Elastic Cloud Serverless"}
                  {deploymentMode === 'cloud' && "Elastic Cloud Hosted"}
                  {deploymentMode === 'standard' && "Self-managed"}
                </EuiText>
              </EuiFlexItem>
            </EuiFlexGroup>
            <EuiSpacer size="s" />
            <EuiFlexGroup alignItems="center">
              <EuiFlexItem grow={false}>
                <EuiIcon size="s" type="tag" />
              </EuiFlexItem>
              <EuiFlexItem grow={true}>
                <EuiText size="s">
                  License: <span style={{ fontWeight: 500 }}>{licenseType || 'unknown'}</span> {!!licenseStatus && licenseStatus !== 'unknown' && <EuiText color="subdued" size="xs" component="span"><small>({licenseStatus})</small></EuiText>}
                </EuiText>
              </EuiFlexItem>
            </EuiFlexGroup>
          </>
        </EuiPopover>,
        <EuiToolTip content={chatOpen ? 'Close AI Agent' : 'Open AI Agent'}>
          <EuiButton
            aria-label={chatOpen ? 'Close AI Agent' : 'Open AI Agent'}
            iconType="productAgent"
            onClick={() => setChatOpen(!chatOpen)}
            style={{ height: '32px', marginLeft: '6px', fontWeight: 500 }}
          >
            AI Agent
          </EuiButton>
        </EuiToolTip>,
      ],
    },
  ]

  ////  Render  ////////////////////////////////////////////////////////////////

  return (
    <div>
      <EuiHeader
        position='fixed'
        sections={headerSections}
        sticky={true}
        style={{ height: '48px', paddingLeft: 0 }}
      />
      <EuiPageTemplate
        contentBorder={false}
        grow={true}
        offset={0}
        paddingSize='s'
        panelled={false}
        responsive={[]}
        restrictWidth={false}
        style={{
          height: 'calc(100vh - 48px)',
          padding: '48px 8px 8px 0'
        }}
      >

        {/* Sidebar (separately scrollable from main content) */}
        <EuiPageTemplate.Sidebar
          paddingSize='none'
          style={{
            height: 'calc(100vh - 48px)',
            minInlineSize: sidebarOpen ? 248 : 48,
            minWidth: sidebarOpen ? 100 : 48,
            width: sidebarOpen ? '100px' : '48px',
          }}>
          <SideNav />
        </EuiPageTemplate.Sidebar>

        {/* Main (separately scrollable from sidebar and chat panel) */}
        <EuiPanel style={{
          borderBottomRightRadius: chatOpen ? 0 : undefined,
          borderTopRightRadius: chatOpen ? 0 : undefined,
          flex: 1,
          height: '100%',
          minWidth: 0,
          overflowY: 'auto',
          paddingSize: 'none',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100%' }}>

            {/* Header */}
            {title &&
              <EuiPageTemplate.Header
                bottomBorder={false}
                pageTitle={title}
                responsive={false}
                rightSideItems={buttons || []}
                style={{ minHeight: '64px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}
              />
            }

            {/* Body */}
            <section style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
              <EuiPanel
                color={'transparent'}
                hasBorder={false}
                hasShadow={false}
                paddingSize={paddingSize}
                style={{
                  borderRadius: 0,
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  minHeight: 0,
                }}
              >
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                  {children}
                </div>
              </EuiPanel>
            </section>

            {/* Notice */}
            <div style={{ flexShrink: 0, marginTop: 'auto', paddingTop: '8px' }}>
              <EuiPanel color='transparent' paddingSize='none'>
                <EuiText color='subdued' size='xs'>
                  <p style={{ fontWeight: 400, fontSize: '11px', lineHeight: '14px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  <EuiIcon type="heart" size="s" style={{ margin: '-2px 6px 0 0' }} />Elasticsearch Relevance Studio is licensed under <a href="https://github.com/elastic/relevance-studio/blob/main/LICENSE.txt" target='_blank' external={false}>Elastic License 2.0</a>, which permits you to use, modify, and distribute the software at no cost.
                  </p>
                </EuiText>
              </EuiPanel>
            </div>
          </div>
        </EuiPanel>
      </EuiPageTemplate>
    </div>
  )
}

export default Page