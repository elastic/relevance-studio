import React from 'react'
import { useRouteMatch } from 'react-router-dom'
import {
  EuiButtonIcon,
  EuiIcon,
  EuiSideNav,
  EuiText,
  EuiToolTip
} from '@elastic/eui'
import {
  IconCodeDots,
  IconScale
} from '@tabler/icons-react'
import { useAppContext } from '../Contexts/AppContext'
import { useProjectContext } from '../Contexts/ProjectContext'

const SideNav = () => {

  const path = useRouteMatch().path

  ////  Context  ///////////////////////////////////////////////////////////////

  const { darkMode, setDarkMode } = useAppContext()

  let project
  try {
    project = useProjectContext().project
  } catch {
    project = null
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const projectItems = () => {
    if (!project)
      return []
    return [
      {
        name: (<>{project.name}</>),
        id: 'project',
        /*href: `#/projects/${project._id}`,*/
        forceOpen: true,
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
            icon: <EuiIcon color='subdued' type='visBarVerticalStacked' size='m' />,
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

  return (<>
    <EuiSideNav
      style={{ width: '100%' }}
      items={items()}
    />
    <div style={{ position: 'fixed', bottom: '10px', left: '10px', right: '10px' }}>
      <EuiToolTip content={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}>
        <EuiButtonIcon
          aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          iconType={darkMode ? 'sun' : 'moon'}
          onClick={() => setDarkMode(!darkMode)}
        />
      </EuiToolTip>
    </div>
  </>)
}

export default SideNav