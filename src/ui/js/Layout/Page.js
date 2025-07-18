import {
  EuiBadge,
  EuiButton,
  EuiButtonIcon,
  EuiHeader,
  EuiIcon,
  EuiPageTemplate,
  EuiPanel,
  EuiProvider,
  EuiText,
  EuiToolTip,
} from '@elastic/eui'
import {
  IconBrandGithub,
} from '@tabler/icons-react'
import { useAppContext } from '../Contexts/AppContext'
import Breadcrumbs from './Breadcrumbs'
import SideNav from './SideNav'

const Page = ({ title, buttons, children, panelled = false, paddingSize = 'l' }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const {
    darkMode,
    deploymentMode,
    sidebarOpen,
    setDarkMode,
    setSidebarOpen,
  } = useAppContext()

  const headerSections = [
    {
      items: [
        <div style={{
          borderRight: `1px solid ${darkMode ? 'rgb(43, 57, 79)' : 'rgb(211, 218, 230)'}`,
          height: '48px',
          marginRight: '8px',
          textAlign: 'center',
          width: '48px',
        }}>
          <EuiButtonIcon
            aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            color='text'
            iconType={sidebarOpen ? 'menuLeft' : 'menuRight'}
            onClick={() => setSidebarOpen(!sidebarOpen)}
            style={{ height: '37px', margin: '6px', width: '35px' }}
          />
        </div>,
        <div style={{ marginLeft: '8px', marginRight: '24px' }}>
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
        </div>,
        <Breadcrumbs />
      ],
    },
    {
      items: [
        <EuiToolTip content={`Switch to ${darkMode ? 'light' : 'dark'} mode`}>
          <EuiButtonIcon
            aria-label={`Switch to ${darkMode ? 'light' : 'dark'} mode`}
            iconType={darkMode ? 'sun' : 'moon'}
            onClick={() => setDarkMode(!darkMode)}
            style={{ height: '38px', marginLeft: '6px', width: '38px' }}
          />
        </EuiToolTip>,
        <EuiToolTip content={'View on Github'}>
          <EuiButton
            aria-label='View on Github'
            color='text'
            style={{
              border: 0,
              height: '38px',
              marginLeft: '6px',
              minWidth: '38px',
              width: '38px'
            }}>
            <a href='https://github.com/elastic/relevance-studio' target='_blank'>
              <IconBrandGithub
                stroke={1.5}
                size={20}
                style={{ marginTop: '4px' }}
              />
            </a>
          </EuiButton>
        </EuiToolTip>,
      ],
    },
  ]

  if (!!deploymentMode) {
    headerSections[1].items.unshift(
      <EuiToolTip content={
        deploymentMode === 'serverless'
          ? 'Running on Elastic Cloud Serverless'
          : deploymentMode === 'cloud'
            ? 'Running on Elastic Cloud'
            : deploymentMode === "standard"
              ? 'Running on Elasticsearch'
              : ''
      }>
        <EuiBadge
          color='hollow'
          iconType={deploymentMode == 'standard' ? 'logoElasticsearch' : 'logoCloud'}
          style={{
            display: 'flex',
            height: '24px',
            marginLeft: '6px',
            marginRight: '6px',
          }}
        >
          <EuiText color='subdued' size='xs' style={{ marginLeft: '3px' }}>
            <small>
              {
                deploymentMode === 'serverless'
                  ? 'Serverless'
                  : deploymentMode === 'cloud'
                    ? 'Cloud'
                    : deploymentMode === 'standard'
                      ? 'Standard'
                      : ''
              }
            </small>
          </EuiText>
        </EuiBadge>
      </EuiToolTip>
    )
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  return (
    <EuiProvider colorMode={darkMode ? 'dark' : 'light'}>
      <EuiHeader position='fixed' sections={headerSections} style={{ paddingLeft: 0 }} />
      <EuiPageTemplate
        bottomBorder='extended'
        grow={true}
        offset={0}
        panelled={false}
        restrictWidth={false}
        style={{ height: '100%', paddingTop: '47px' }}
      >

        {/* Sidebar (separately scrollable from main content) */}
        {sidebarOpen &&
          <EuiPageTemplate.Sidebar
            paddingSize='none'
            style={{
              height: 'calc(100vh - 48px)',
              minInlineSize: 248,
              minWidth: 248,
              width: '248px',
            }}>
            <SideNav />
          </EuiPageTemplate.Sidebar>
        }

        {/* Main (separately scrollable from sidebar) */}
        <div style={{ height: 'calc(100vh - 48px)', overflow: 'scroll' }}>
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

            {/* Header */}
            {title &&
              <EuiPageTemplate.Header
                pageTitle={title}
                rightSideItems={buttons || []}
                style={{ minHeight: '90px' }}
              />
            }

            {/* Body */}
            <section style={{ display: 'flex', flex: 1, minHeight: 0 }}>
              <EuiPanel
                color={panelled ? 'subdued' : 'plain'}
                hasBorder={false}
                hasShadow={!panelled}
                paddingSize={panelled ? 'm' : paddingSize}
                style={{
                  borderRadius: 0,
                  height: '100%',
                  display: 'flex'
                }}
              >
                <div style={{ flex: 1 }}>
                  {children}
                </div>
              </EuiPanel>
            </section>
          </div>
        </div>
      </EuiPageTemplate>
    </EuiProvider>
  )
}

export default Page