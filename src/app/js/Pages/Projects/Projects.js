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
        response = await api.get_projects()
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to get projects' }))
      } finally {
        setIsLoadingProjects(false)
      }

      // Handle API response
      setProjects(utils.toMap(utils.hitsToDocs(response)))
      const aggs = {}
      if (response.data.aggregations.counts) {
        response.data.aggregations.counts.buckets.forEach(agg => {
          aggs[agg.key] = {
            displays: agg.displays.doc_count,
            scenarios: agg.scenarios.doc_count,
            judgements: agg.judgements.doc_count,
            strategies: agg.strategies.doc_count,
            evaluations: agg.evaluations.doc_count,
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
        field: 'displays',
        name: 'Displays',
        render: (name, doc) => (
          <EuiLink href={`#/projects/${doc._id}/displays`}>
            {projectsAggs[doc._id]?.displays.toLocaleString() || 0}
          </EuiLink>
        ),
      },
      {
        field: 'scenarios',
        name: 'Scenarios',
        render: (name, doc) => (
          <EuiLink href={`#/projects/${doc._id}/scenarios`}>
            {projectsAggs[doc._id]?.scenarios.toLocaleString() || 0}
          </EuiLink>
        ),
      },
      {
        field: 'judgements',
        name: 'Judgements',
        render: (name, doc) => (
          <EuiLink href={`#/projects/${doc._id}/judgements`}>
            {projectsAggs[doc._id]?.judgements.toLocaleString() || 0}
          </EuiLink>
        ),
      },
      {
        field: 'strategies',
        name: 'Strategies',
        render: (name, doc) => (
          <EuiLink href={`#/projects/${doc._id}/strategies`}>
            {projectsAggs[doc._id]?.strategies.toLocaleString() || 0}
          </EuiLink>
        ),
      },
      {
        field: 'evaluations',
        name: 'Evaluations',
        render: (name, doc) => (
          <EuiLink href={`#/projects/${doc._id}/evaluations`}>
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
          {doc.rating_scale.max == 1 ? 'binary' : 'graded'}
        </>),
      },
      {
        name: 'Actions',
        actions: [
          {
            color: 'text',
            description: 'Update this project',
            icon: 'documentEdit',
            name: 'update',
            onClick: (doc) => setFlyout(doc),
            type: 'icon',
          },
          {
            color: 'danger',
            description: 'Delete this project',
            icon: 'trash',
            name: 'delete',
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
        doc={modalDelete}
        docType='project'
        isLoading={isLoadingProject}
        onClose={() => setModalDelete(null)}
        onError={(err) => addToast(api.errorToast(err, { title: `Failed to delete project` }))}
        onDelete={async () => {
          setIsLoadingProject(true)
          try {
            await api.delete_project(modalDelete._id)
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