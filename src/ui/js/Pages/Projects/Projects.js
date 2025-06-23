import React, { useEffect, useMemo, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiInMemoryTable,
  EuiLink,
  EuiSkeletonText,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { ModalDelete, Page } from '../../Layout'
import FlyoutForm from './FlyoutForm'
import api from '../../api'
import utils from '../../utils'

const Projects = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [projects, setProjects] = useState({})
  const [projectsAggs, setProjectsAggs] = useState({})
  const [isLoadingProjects, setIsLoadingProjects] = useState(true)
  const [isLoadingProject, setIsLoadingProject] = useState(false)

  /**
   * Scenarios as an array for the table component
   */
  const projectsList = Object.values(projects) || []

  /**
   * null:   close flyout
   * true:   open flyout to create a new doc
   * object: open flyout to update a given doc (object)
   */
  const [flyout, setFlyout] = useState(null)

  /**
   * null:   close modal
   * object: open modal to delete a given doc (object)
   */
  const [modalDelete, setModalDelete] = useState(null)

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Get projects on load
   */
  useEffect(() => {
    (async () => {

      // Submit API request
      let response
      try {
        setIsLoadingProjects(true)
        response = await api.projects_browse()
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to get projects' }))
      } finally {
        setIsLoadingProjects(false)
      }

      // Handle API response
      setProjects(utils.toMap(utils.hitsToDocs(response)))
      const aggs = {}
      if (response.data.aggregations?.counts?.buckets) {
        response.data.aggregations.counts.buckets.forEach(agg => {
          aggs[agg.key] = {
            displays: agg.displays?.doc_count || 0,
            scenarios: agg.scenarios?.doc_count || 0,
            judgements: agg.judgements?.doc_count || 0,
            strategies: agg.strategies?.doc_count || 0,
            evaluations: agg.evaluations?.doc_count || 0,
          }
        })
      }
      setProjectsAggs(aggs)
    })()
  }, [])

  /**
   * Log projects state
   */
  useEffect(() => {
    if (!projects)
      return
    console.debug('[Projects state updated]', {
      projects: projects,
      projectsAggs: projectsAggs
    })
  }, [projects])

  ////  Render  ////////////////////////////////////////////////////////////////

  const columns = useMemo(() => {
    return [
      {
        field: 'name',
        name: 'Name',
        sortable: true,
        truncateText: true,
        render: (name, doc) => (<>{doc.name}</>),
      },
      {
        field: 'scenarios',
        name: 'Scenarios',
        sortable: true,
        render: (name, doc) => (
          <EuiLink href={`#/projects/${doc._id}/scenarios`}>
            {projectsAggs[doc._id]?.scenarios.toLocaleString() || 0}
          </EuiLink>
        ),
      },
      {
        field: 'judgements',
        name: 'Judgements',
        sortable: true,
        render: (name, doc) => (
          <EuiLink href={`#/projects/${doc._id}/judgements`}>
            {projectsAggs[doc._id]?.judgements.toLocaleString() || 0}
          </EuiLink>
        ),
      },
      {
        field: 'strategies',
        name: 'Strategies',
        sortable: true,
        render: (name, doc) => (
          <EuiLink href={`#/projects/${doc._id}/strategies`}>
            {projectsAggs[doc._id]?.strategies.toLocaleString() || 0}
          </EuiLink>
        ),
      },
      {
        field: 'benchmarks',
        name: 'Benchmarks',
        sortable: true,
        render: (name, doc) => (
          <EuiLink href={`#/projects/${doc._id}/benchmarks`}>
            {projectsAggs[doc._id]?.evaluations.toLocaleString() || 0}
          </EuiLink>
        ),
      },
      {
        field: 'indices',
        name: 'Indices',
        render: (name, doc) => {
          const patterns = [];
          (doc.index_pattern || '').split(',').forEach((pattern, i) => {
            patterns.push(
              <EuiBadge color='hollow' key={i}>
                {pattern}
              </EuiBadge>
            )
          })
          return patterns
        },
      },
      {
        field: 'rating_scale',
        name: 'Rating scale',
        render: (name, doc) => (<>
          {doc.rating_scale.min} <span style={{ fontSize: '10px', padding: '0 4px' }}>{'-->'}</span> {doc.rating_scale.max}
        </>),
      },
      {
        name: 'Actions',
        actions: [
          {
            color: 'text',
            description: 'Manage displays',
            icon: 'palette',
            isPrimary: true,
            name: 'Displays',
            onClick: (doc) => {
              window.location.href = `/#/projects/${doc._id}/displays`
            },
            type: 'icon'
          },
          {
            color: 'text',
            description: 'Update this project',
            icon: 'documentEdit',
            isPrimary: true,
            name: 'Update',
            onClick: (doc) => setFlyout(doc),
            type: 'icon',
          },
          {
            color: 'danger',
            description: 'Delete this project',
            icon: 'trash',
            name: 'Delete',
            onClick: (doc) => setModalDelete(doc),
            type: 'icon',
          }
        ],
      }
    ]
  }, [projects])


  ////  Render  ////////////////////////////////////////////////////////////////

  const buttonCreate = (
    <EuiButton
      fill
      iconType='plusInCircle'
      onClick={() => setFlyout(true)}>
      Create a new project
    </EuiButton>
  )

  return (<>
    {modalDelete &&
      <ModalDelete
        description={
          !!Object.keys((projectsAggs[modalDelete._id]) || {}).length &&
          <EuiText>
            <p>This will delete all assets related to this project:</p>
            <ul>
              {!!projectsAggs[modalDelete._id]?.displays &&
                <li>{projectsAggs[modalDelete._id]?.displays || 0} display{projectsAggs[modalDelete._id]?.displays == 1 ? '' : 's'}</li>
              }
              {!!projectsAggs[modalDelete._id]?.scenarios &&
                <li>{projectsAggs[modalDelete._id]?.scenarios || 0} scenario{projectsAggs[modalDelete._id]?.scenarios == 1 ? '' : 's'}</li>
              }
              {!!projectsAggs[modalDelete._id]?.judgements &&
                <li>{projectsAggs[modalDelete._id]?.judgements || 0} judgement{projectsAggs[modalDelete._id]?.judgements == 1 ? '' : 's'}</li>
              }
              {!!projectsAggs[modalDelete._id]?.strategies &&
                <li>{projectsAggs[modalDelete._id]?.strategies || 0} {projectsAggs[modalDelete._id]?.strategies == 1 ? 'strategy' : 'strategies'}</li>
              }
              {!!projectsAggs[modalDelete._id]?.evaluations &&
                <li>{projectsAggs[modalDelete._id]?.evaluations || 0} evaluation{projectsAggs[modalDelete._id]?.evaluations == 1 ? '' : 's'}</li>
              }
            </ul>
          </EuiText>
        }
        doc={modalDelete}
        docType='project'
        isLoading={isLoadingProject}
        onClose={() => setModalDelete(null)}
        onError={(err) => addToast(api.errorToast(err, { title: `Failed to delete project` }))}
        onDelete={async () => {
          setIsLoadingProject(true)
          try {
            await api.projects_delete(modalDelete._id)
          } finally {
            setIsLoadingProject(false)
          }
        }}
        onDeleted={(doc) => {
          setProjects(prev => {
            const { [doc._id]: _, ...rest } = prev
            return rest
          })
          setProjectsAggs(prev => {
            const { [doc._id]: _, ...rest } = prev
            return rest
          })
          setModalDelete(null)
        }}
      />
    }
    {flyout &&
      <FlyoutForm
        action={flyout === true ? 'create' : 'update'}
        doc={flyout}
        onClose={() => setFlyout(null)}
        onCreated={(newDoc) => {
          // Redirect to displays
          window.location.href = `/#/projects/${newDoc._id}/displays`
        }}
        onUpdated={(newDoc) => {
          // Update doc in table
          setProjects(prev => ({ ...prev, [newDoc._id]: newDoc }))
        }}
      />
    }
    <Page title='Projects' buttons={[buttonCreate]}>
      <EuiSkeletonText lines={10} isLoading={isLoadingProjects}>
        {!projectsList.length &&
          <EuiCallOut
            color='primary'
            title='Welcome!'
          >
            <EuiText>
              Create your first project to get started.
            </EuiText>
            <EuiSpacer size='m' />
            <EuiButton
              fill
              iconType='plusInCircle'
              onClick={() => setFlyout(true)}>
              Create a new project
            </EuiButton>
          </EuiCallOut>
        }
        {!!projectsList.length &&
          <EuiInMemoryTable
            columns={columns}
            items={projectsList}
            pagination={true}
            responsiveBreakpoint={false}
            sorting={{
              sort: {
                field: 'name',
                direction: 'asc',
              }
            }}
          />
        }
      </EuiSkeletonText>
    </Page>
  </>)
}

export default Projects