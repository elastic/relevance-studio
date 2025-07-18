import { useRouteMatch } from 'react-router-dom'
import {
  EuiIcon,
  EuiPanel,
  EuiSideNav,
  EuiText,
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

  const { sidebarOpen } = useAppContext()

  // Do this in case the sidebar is on a page that isn't in ResourceProvider
  const useSafePageResources = () => {
    try {
      return usePageResources()
    } catch (error) {
      return {}
    }
  }
  const { project } = useSafePageResources()

  ////  Render  ////////////////////////////////////////////////////////////////

  const projectItems = () => {
    if (!project)
      return []
    return [
      {
        name: (<>{project.name}</>),
        id: 'project',
        href: `#/projects/${project._id}`,
        forceOpen: true,
        isSelected: path == '/projects/:project_id',
        items: [
          {
            name: 'Displays',
            id: 'displays',
            icon: <EuiIcon color='subdued' type='palette' size='m' />,
            href: `#/projects/${project._id}/displays`,
            isSelected: path.startsWith('/projects/:project_id/displays'),
          },
          {
            name: 'Scenarios',
            id: 'scenarios',
            icon: <EuiIcon color='subdued' type='comment' size='m' />,
            href: `#/projects/${project._id}/scenarios`,
            isSelected: path.startsWith('/projects/:project_id/scenarios'),
          },
          {
            name: 'Judgements',
            id: 'judgements',
            icon: <EuiText color='subdued' style={{ marginBottom: '-4px' }}><IconScale stroke={1.5} size={16} /></EuiText>,
            href: `#/projects/${project._id}/judgements`,
            isSelected: path.startsWith('/projects/:project_id/judgements'),
          },
          {
            name: 'Strategies',
            id: 'strategies',
            icon: <EuiText color='subdued' style={{ marginBottom: '-4px' }}><IconCodeDots stroke={1.5} size={16} /></EuiText>,
            href: `#/projects/${project._id}/strategies`,
            isSelected: path.startsWith('/projects/:project_id/strategies'),
          },
          {
            name: 'Benchmarks',
            id: 'benchmarks',
            icon: <EuiIcon color='subdued' type='stats' size='m' />,
            href: `#/projects/${project._id}/benchmarks`,
            isSelected: path.startsWith('/projects/:project_id/benchmarks'),
          }
        ]
      }
    ]
  }

  const items = () => [
    {
      name: 'Relevance Studio',
      id: 'sidenav',
      href: '#/',
      isSelected: path.hash == '#/',
      items: [
        {
          name: 'Projects',
          id: 'projects',
          href: '#/projects',
          isSelected: path == '/projects',
          items: projectItems()
        }
      ],
    },
  ]

  return (
    <EuiPanel
      color='plain'
      style={{
        borderRadius: 0,
        height: '100%',
        zIndex: 99
      }}
    >
      {sidebarOpen &&
        <>
          <EuiSideNav
            style={{ marginTop: '-3px', width: '100%' }}
            items={items()}
          />
          <EuiPanel
            color='subdued'
            paddingSize='s'
            style={{
              position: 'absolute',
              bottom: '8px',
              left: '8px',
              right: '8px'
            }}>
            <EuiText color='subdued' size='xs'>
              <p style={{ fontWeight: 400, fontSize: '11px', lineHeight: '14px' }}>
                Elasticsearch Relevance Studio is a community project maintained by the Search AI Solutions Architects at Elastic. It's not covered by Elastic Support.
              </p>
            </EuiText>
          </EuiPanel>
        </>
      }
      {!sidebarOpen &&
        <EuiIcon type='logoElasticsearch' />
      }
    </EuiPanel>
  )
}

export default SideNav