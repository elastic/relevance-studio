import React, { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiForm,
  EuiInMemoryTable,
  EuiLink,
  EuiModal,
  EuiModalHeaderTitle,
  EuiModalBody,
  EuiModalFooter,
  EuiModalHeader,
  EuiSkeletonText,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import api from '../../api'
import utils from '../../utils'
import { Page } from '../../Layout'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'

const Evaluations = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const { project, loadingProject } = useProjectContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [items, setItems] = useState([])
  const [loadingItems, setLoadingItems] = useState(true)
  const [loadingModal, setLoadingModal] = useState(false)
  const [runningEvaluation, setRunningEvaluation] = useState(false)
  const [modalData, setModalData] = useState({})
  const [modalDeleteVisible, setModalDeleteVisible] = useState(false)

  /**
   * Get evaluations on load
   */
  useEffect(() => {
    if (!project?._id)
      return
    (async () => {
    
      // Submit API request
      let response
      try {
        setLoadingItems(true)
        response = await api.get_evaluations(project._id)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to get evaluations'
        }))
      } finally {
        setLoadingItems(false)
      }

      // Handle API response
      const items = []
      response.data.hits.hits.forEach(doc => {
        const item = doc._source
        item._id = doc._id
        items.push(item)
      })
      setItems(items)
    })()
  }, [project])
  
  const onRunEvaluationSubmit = (e) => {
    e.preventDefault();
    (async () => {
      try {
        setRunningEvaluation(true)

        // Get strategies
        let strategies = []
        try {
          const res1 = await api.get_strategies(project._id)
          res1.data.hits.hits.forEach(doc => {
            strategies.push(doc._id)
          })
        } catch (error) {
          return addToast(api.errorToast(error, {
            title: 'Failed to get strategies for evaluation'
          }))
        }

        // Get scenarios
        let scenarios = []
        try {
          const res2 = await api.get_scenarios(project._id)
          res2.data.hits.hits.forEach(doc => {
            scenarios.push(doc._id)
          })
        } catch (error) {
          return addToast(api.errorToast(error, {
            title: 'Failed to get scenarios for evaluation'
          }))
        }
      
        // Submit API request
        const params = {
          store_results: 'true'
        }
        const body = {
          strategies: strategies,
          scenarios: scenarios,
          metrics: [ 'ndcg', 'precision', 'recall' ],
          k: 10,
        }
        let response
        try {
          setRunningEvaluation(true)
          response = await api.run_evaluation(project._id, body, params)
        } catch (error) {
          return addToast(api.errorToast(error, {
            title: 'Failed to run evaluation'
          }))
        } finally {
          setRunningEvaluation(false)
        }

        // Handle API response
        if (response.status < 200 && response.status > 299)
          addToast(utils.toastClientResponse(response))

        // Redirect to scenarios on success
        window.location.href = `/#/projects/${project._id}/evaluations/${response.data._id}`
        addToast({
          title: 'Ran evaluation',
          color: 'success',
          iconType: 'check'
        })

      } finally {
        setRunningEvaluation(false)
      }
    })()
  }

  const onModalDeleteSubmit = (e) => {
    e.preventDefault();
    (async () => {
    
      // Submit API request
      const doc = { ...modalData }
      let response
      try {
        setLoadingModal(true)
        response = await api.delete_evaluation(project._id, modalData._id)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to delete display'
        }))
      } finally {
        setLoadingModal(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Deleted evaluation',
        color: 'success',
        iconType: 'check',
        text: (
          <EuiText size='xs'>
            <b>{modalData._id}</b><br />
            <EuiText color='subdued' size='xs'>{modalData._id}</EuiText>
          </EuiText>
        )
      })
      setItems(items.filter(item => item._id !== modalData._id))
      onModalDeleteClose()
    })()
  }

  ////  Handlers: Modal open and close  ////////////////////////////////////////

  const onModalDeleteOpen = (item) => {
    setModalData(item)
    setModalDeleteVisible(true)
  }

  const onModalDeleteClose = () => {
    setModalData({})
    setModalDeleteVisible(false)
  }

  ////  Elements: Modals  //////////////////////////////////////////////////////

  /**
   * Modal to delete an evaluation.
   */
  const modalDelete = (
    <EuiModal onClose={onModalDeleteClose}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          Delete <b>{modalData._id}</b>?
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiForm component='form' id='delete'>
          <EuiText color='subdued' size='xs'>Evaluation _id:<br /><b>{modalData._id}</b></EuiText>
          <EuiSpacer size='m' />
          <EuiText>This action can't be undone.</EuiText>
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          color='danger'
          disabled={loadingModal}
          fill
          form='modal-delete'
          isLoading={loadingModal}
          onClick={onModalDeleteSubmit}
          type='submit'
        >
          Delete
        </EuiButton>
        <EuiButton
          color='text'
          disabled={loadingModal}
          onClick={onModalDeleteClose}
        >
          Cancel
        </EuiButton>
      </EuiModalFooter>
    </EuiModal>
  )

  ////  Render  ////////////////////////////////////////////////////////////////

  const tableColumns = [
    {
      field: '_id',
      name: 'Evaluation',
      sortable: true,
      truncateText: true,
      render: (name, item) => (
        <EuiLink href={`#/projects/${project._id}/evaluations/${item._id}`}>
          {item._id}
        </EuiLink>
      )
    },
    {
      field: 'metrics',
      name: 'Metrics',
      truncateText: true,
      render: (name, item) => {
        const metrics = []
        item.config.metrics.forEach((metric) => {
          metrics.push(<EuiBadge color='hollow' key={metric}>{metric}</EuiBadge>)
        })
        return metrics
      }
    },
    {
      field: 'num_strategies',
      name: 'Strategies',
      sortable: true,
      render: (name, item) => item.strategy_id.length
    },
    {
      field: 'num_scenarios',
      name: 'Scenarios',
      sortable: true,
      render: (name, item) => item.scenario_id.length
    },
    {
      field: '@timestamp',
      name: 'Time run',
      sortable: true,
      render: (name, item) => new Date(item['@timestamp']).toLocaleString()
    },
    {
      name: 'Actions',
      actions: [
        {
          color: 'danger',
          description: 'Delete this strategy',
          icon: 'trash',
          name: 'delete',
          onClick: onModalDeleteOpen,
          type: 'icon',
        }
      ],
    }
  ]

  /**
   * Button that navigates to the page to create an evaluation.
   */
  const buttonCreate = (
    <EuiButton
      fill
      iconType='plusInCircle'
      isLoading={runningEvaluation}
      onClick={onRunEvaluationSubmit}>
      Run evaluation
    </EuiButton>
  )

  return (<>
    {modalDeleteVisible && modalDelete}
    <Page title='Evaluations' buttons={[buttonCreate]}>
      <EuiSkeletonText lines={10} isLoading={loadingItems || loadingProject}>
        {!items.length &&
          <EuiCallOut
            color='primary'
            title='Welcome!'
          >
            <EuiText>
              Create your first evaluation to get started.
            </EuiText>
            <EuiSpacer size='m' />
            {buttonCreate}
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
                field: '@timestamp',
                direction: 'desc',
              }
            }}
            tableLayout='auto'
          />
        }
      </EuiSkeletonText>
    </Page>
  </>)
}

export default Evaluations