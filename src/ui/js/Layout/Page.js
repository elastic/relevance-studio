import {
  EuiPageTemplate,
  EuiPanel,
  EuiProvider,
} from '@elastic/eui'
import { useAppContext } from '../Contexts/AppContext'
import SideNav from './SideNav'

const Page = ({ title, buttons, children, panelled = false, paddingSize = 'l' }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { darkMode } = useAppContext()

  ////  Render  ////////////////////////////////////////////////////////////////

  return (
    <EuiProvider colorMode={darkMode ? 'dark' : 'light'}>
      <EuiPageTemplate
        bottomBorder='extended'
        grow={true}
        offset={0}
        panelled={false}
        restrictWidth={false}
      >

        {/* Sidebar (separately scrollable from main content) */}
        <EuiPageTemplate.Sidebar paddingSize='none' style={{ height: '100vh' }}>
          <SideNav />
        </EuiPageTemplate.Sidebar>

        {/* Main (separately scrollable from sidebar) */}
        <div style={{ height: '100vh', overflow: 'scroll' }}>
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

            {/* Header */}
            <EuiPageTemplate.Header
              pageTitle={title}
              rightSideItems={buttons || []}
              style={{ minHeight: '90px' }}
            />

            {/* Body */}
            <section style={{ flex: 1 }}>
              <EuiPanel
                color={panelled ? 'subdued' : 'plain'}
                hasBorder={false}
                hasShadow={!panelled}
                paddingSize={panelled ? 'm' : paddingSize}
                style={{
                  borderRadius: 0,
                  height: '100%',
                }}
              >
                {children}
              </EuiPanel>
            </section>
          </div>
        </div>
      </EuiPageTemplate>
    </EuiProvider>
  )
}

export default Page