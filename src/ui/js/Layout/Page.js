import { EuiPageTemplate, EuiProvider } from '@elastic/eui'
import { useAppContext } from '../Contexts/AppContext'
import SideNav from './SideNav'

const Page = ({ title, buttons, children }) => {

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
        <EuiPageTemplate.Sidebar paddingSize='m'>
          <SideNav />
        </EuiPageTemplate.Sidebar>
        <EuiPageTemplate.Header
          pageTitle={title}
          rightSideItems={buttons || []}
          style={{ minHeight: '90px' }}
        />
        <EuiPageTemplate.Section
          bottomBorder={false}
          color='plain'
          grow={true}
        >
          {children}
        </EuiPageTemplate.Section>
      </EuiPageTemplate>
    </EuiProvider>
  )
}

export default Page