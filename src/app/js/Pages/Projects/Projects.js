import React, { useEffect, useState } from 'react'
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
import api from '../../api'
import { useAppContext } from '../../Contexts/AppContext'
import { ModalDelete, Page } from '../../Layout'
import FlyoutForm from './FlyoutForm'

const Projects = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [aggs, setAggs] = useState({})
  const [flyout, setFlyout] = useState(null) // null=closed, true=create, object=doc to update
  const [isLoading, setIsLoading] = useState(true) // start as loading until project is ready
  const [items, setItems] = useState([])
  const [modalDelete, setModalDelete] = useState(null) // null=closed, object=doc to delete

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Get projects on load
   */
  useEffect(() => {
    (async () => {
      
      // Submit API request
      let response
      try {
        setIsLoading(true)
        response = await api.get_projects()
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to get projects' }))
      } finally {
        setIsLoading(false)
      }

      // Handle API response
      const items = []
      response.data.hits.hits.forEach(doc => {
        const item = doc._source
        item._id = doc._id
        items.push(item)
      })
      setItems(items)
      const aggs = {}
      if (response.data.aggregations.projects) {
        response.data.aggregations.projects.buckets.forEach(agg => {
          aggs[agg.key] = {
            displays: agg.displays.doc_count,
            scenarios: agg.scenarios.doc_count,
            judgements: agg.judgements.doc_count,
            strategies: agg.strategies.doc_count,
            evaluations: agg.evaluations.doc_count,
          }
        })
      }
      setAggs(aggs)
    })()
  }, [])

  ////  Render  ////////////////////////////////////////////////////////////////

  const tableColumns = [
    {
      field: 'name',
      name: 'Name',
      sortable: true,
      truncateText: true,
      render: (name, item) => (<>{item.name}</>),
    },
    {
      field: 'displays',
      name: 'Displays',
      render: (name, item) => (
        <EuiLink href={`#/projects/${item._id}/displays`}>
          {aggs[item._id]?.displays.toLocaleString() || 0}
        </EuiLink>
      ),
    },
    {
      field: 'scenarios',
      name: 'Scenarios',
      render: (name, item) => (
        <EuiLink href={`#/projects/${item._id}/scenarios`}>
          {aggs[item._id]?.scenarios.toLocaleString() || 0}
        </EuiLink>
      ),
    },
    {
      field: 'judgements',
      name: 'Judgements',
      render: (name, item) => (
        <EuiLink href={`#/projects/${item._id}/judgements`}>
          {aggs[item._id]?.judgements.toLocaleString() || 0}
        </EuiLink>
      ),
    },
    {
      field: 'strategies',
      name: 'Strategies',
      render: (name, item) => (
        <EuiLink href={`#/projects/${item._id}/strategies`}>
          {aggs[item._id]?.strategies.toLocaleString() || 0}
        </EuiLink>
      ),
    },
    {
      field: 'evaluations',
      name: 'Evaluations',
      render: (name, item) => (
        <EuiLink href={`#/projects/${item._id}/evaluations`}>
          {aggs[item._id]?.evaluations.toLocaleString() || 0}
        </EuiLink>
      ),
    },
    {
      field: 'indices',
      name: 'Indices',
      render: (name, item) => {
        const patterns = [];
        (item.index_pattern || '').split(',').forEach((pattern, i) => {
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
      render: (name, item) => (<>
        {item.rating_scale.max == 1 ? 'binary' : 'graded'}
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
          onClick: (item) => setFlyout(item),
          type: 'icon',
        },
        {
          color: 'danger',
          description: 'Delete this project',
          icon: 'trash',
          name: 'delete',
          onClick: (item) => setModalDelete(item),
          type: 'icon',
        }
      ],
    }
  ]


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
        onClose={() => setModalDelete(null)}
        onDeleted={() => {
          // Remove doc from table
          setItems(items.filter(item => item._id !== modalDelete._id))
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
          setItems(prev => prev.map(item => item._id === newDoc._id ? newDoc : item))
        }}
      />
    }
    <Page title='Projects' buttons={[buttonCreate]}>
      <EuiSkeletonText lines={10} isLoading={isLoading}>
        {!items.length &&
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
        {!!items.length &&
          <EuiInMemoryTable
            columns={tableColumns}
            items={items}
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