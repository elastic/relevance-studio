import {
  EuiButton,
  EuiButtonIcon,
  EuiHeader,
  EuiHeaderLogo,
  EuiPageTemplate,
  EuiPanel,
  EuiProvider,
  EuiToolTip,
} from '@elastic/eui'
import {
  IconBrandGithub,
} from '@tabler/icons-react'
import { useAppContext } from '../Contexts/AppContext'
import SideNav from './SideNav'

const Page = ({ title, buttons, children, panelled = false, paddingSize = 'l' }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const {
    darkMode,
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
            color='text'
            iconType={sidebarOpen ? 'menuLeft' : 'menuRight'}
            onClick={() => setSidebarOpen(!sidebarOpen)}
            style={{ height: '37px', margin: '6px', width: '35px' }}
          />
        </div>,
        <div style={{ textAlign: 'center', width: '56px' }}>
          <EuiHeaderLogo />
        </div>,
      ],
    },
    {
      items: [
        <EuiToolTip content={'View on Github'}>
          <EuiButton
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
        <EuiToolTip content={`Switch to ${darkMode ? 'dark' : 'light'} mode`}>
          <EuiButtonIcon
            aria-label={`Switch to ${darkMode ? 'dark' : 'light'} mode`}
            iconType={darkMode ? 'sun' : 'moon'}
            onClick={() => setDarkMode(!darkMode)}
            style={{ height: '38px', marginLeft: '6px', width: '38px' }}
          />
        </EuiToolTip>,
      ],
    },
  ]

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
        <EuiPageTemplate.Sidebar
          paddingSize='none'
          style={{
            height: 'calc(100vh - 48px)',
            minInlineSize: sidebarOpen ? 248 : 47,
            minWidth: sidebarOpen ? 248 : 47,
            width: sidebarOpen ? '248px' : '47px',
          }}>
          <SideNav />
        </EuiPageTemplate.Sidebar>

        {/* Main (separately scrollable from sidebar) */}
        <div style={{ height: 'calc(100vh - 48px)', overflow: 'scroll' }}>
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

            {/* Header */}
            <EuiPageTemplate.Header
              pageTitle={title}
              rightSideItems={buttons || []}
              style={{ minHeight: '90px' }}
            />

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