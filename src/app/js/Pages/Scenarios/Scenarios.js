import React, { useEffect, useState } from 'react'
import { useHistory } from 'react-router-dom'
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
import { ModalDelete, Page } from '../../Layout'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'
import FlyoutForm from './FlyoutForm'

const Scenarios = () => {

  const history = useHistory()

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, darkMode } = useAppContext()
  const { project, loadingProject } = useProjectContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [aggs, setAggs] = useState({})
  const [flyout, setFlyout] = useState(null) // null=closed, true=create, object=doc to update
  const [items, setItems] = useState([])
  const [isLoading, setIsLoading] = useState(true) // start as loading until project is ready
  const [modalDelete, setModalDelete] = useState(null) // null=closed, object=doc to delete

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Get scenarios on load
   */
  useEffect(() => {
    if (!project?._id)
      return
    (async () => {

      // Submit API request
      let response
      try {
        setIsLoading(true)
        response = await api.get_scenarios(project._id)
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to get scenarios' }))
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
      response.data.aggregations.scenarios?.buckets.forEach(agg => {
        aggs[agg.key] = {
          ...aggs[agg.key] || {},
          judgements: agg.judgements.doc_count,
          //evaluations: agg.evaluations.doc_count
        }
      })
      setAggs(aggs)
    })()
  }, [project])

  ////  Render  ////////////////////////////////////////////////////////////////

  const tableColumns = [
    {
      field: 'name',
      name: 'Scenario',
      sortable: true,
      truncateText: true,
      render: (name, item) => <>{item.name}</>
    },
    {
      field: 'judgements',
      name: 'Judgements',
      render: (name, item) => {
        return (
          <EuiLink onClick={(e) => {
            history.push({
              pathname: `/projects/${project._id}/judgements`,
              state: {
                query_on_load: {
                  scenario: item,
                  filter: 'rated'
                }
              }
            })
          }}>
            {aggs[item._id]?.judgements.toLocaleString() || 0}
          </EuiLink>
        )
      }
    },
    /*{
      field: 'evaluations',
      name: 'Evaluations',
      render: (name, item) => {
        return (
          <EuiLink href={`#/projects/${project._id}/evaluations`}>
            {aggs[item._id]?.evaluations.toLocaleString() || 0}
          </EuiLink>
        )
      }
    },*/
    {
      field: 'values',
      name: 'Values',
      render: (name, item) => {
        const values = []
        for (const param in item.values)
          values.push(
            <EuiBadge color='hollow' key={param}>
              {param}: {item.values[param]}
            </EuiBadge>
          )
        if (!values.length)
          return <EuiBadge color='warning' iconType='warningFilled' size='xs'>none</EuiBadge>
        return values
      },
    },
    {
      field: 'tags',
      name: 'Tags',
      render: (name, item) => {
        const tags = []
        for (var i in item.tags)
          tags.push(
            <EuiBadge color='hollow' key={item.tags[i]}>
              {item.tags[i]}
            </EuiBadge>
          )
        return tags
      },
    },
    {
      name: 'Actions',
      actions: [
        {
          color: 'text',
          description: 'Update this scenario',
          icon: 'documentEdit',
          name: 'update',
          onClick: (item) => setFlyout(item),
          type: 'icon',
        },
        {
          color: 'danger',
          description: 'Delete this scenario',
          icon: 'trash',
          name: 'delete',
          onClick: (item) => setModalDelete(item),
          type: 'icon',
        }
      ],
    }
  ]

  const buttonCreate = (
    <EuiButton
      fill
      iconType='plusInCircle'
      onClick={() => setFlyout(true)}>
      Create a new scenario
    </EuiButton>
  )

  return (<>
    {modalDelete &&
      <ModalDelete
        doc={modalDelete}
        docType='scenario'
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
          // Add doc to table
          const item = { ...newDoc }
          setItems(prev => [...prev, item])
        }}
        onUpdated={(newDoc) => {
          // Update doc in table
          setItems(prev => prev.map(item => item._id === newDoc._id ? newDoc : item))
        }}
      />
    }
    <Page title='Scenarios' buttons={[buttonCreate]}>
      <EuiSkeletonText lines={10} isLoading={isLoading || loadingProject}>
        {!items.length &&
          <EuiCallOut
            color='primary'
            title='Welcome!'
          >
            <EuiText>
              Create your first scenario to get started.
            </EuiText>
            <EuiSpacer size='m' />
            <EuiButton
              fill
              iconType='plusInCircle'
              onClick={() => setFlyout(true)}>
              Create a new scenario
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
            tableLayout='auto'
          />
        }
      </EuiSkeletonText>
    </Page>
  </>)
}

export default Scenarios