import React, { useEffect, useState } from 'react'
import {
  EuiButton,
  EuiCallOut,
  EuiCode,
  EuiFieldText,
  EuiFlexGroup,
  EuiFlexItem,
  EuiForm,
  EuiFormRow,
  EuiInMemoryTable,
  EuiLink,
  EuiModal,
  EuiModalBody,
  EuiModalFooter,
  EuiModalHeader,
  EuiModalHeaderTitle,
  EuiRadioGroup,
  EuiSkeletonText,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import api from '../../api'
import utils from '../../utils'
import { useAppContext } from '../../Contexts/AppContext'
import { Page } from '../../Layout'

const Projects = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [aggs, setAggs] = useState({})
  const [items, setItems] = useState([])
  const [loadingItems, setLoadingItems] = useState(true)
  const [loadingModal, setLoadingModal] = useState(false)
  const [modalData, setModalData] = useState({})
  const [modalCreateVisible, setModalCreateVisible] = useState(false)
  const [modalUpdateVisible, setModalUpdateVisible] = useState(false)
  const [modalDeleteVisible, setModalDeleteVisible] = useState(false)

  /**
   * Get projects on load
   */
  useEffect(() => {
    (async () => {

      // Submit API request
      let response
      try {
        setLoadingItems(true)
        response = await api.get_projects()
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to get projects'
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
      const aggs = {}
      if (response.data.aggregations.projects) {
        response.data.aggregations.projects.buckets.forEach(agg => {
          aggs[agg.key] = {
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


  ////  Handlers: Modal submission  ////////////////////////////////////////////

  const onModalCreateSubmit = (e) => {
    e.preventDefault();
    (async () => {

      // Submit API request
      const doc = {
        name: modalData.name,
        indices: modalData.indices,
        rating_scale: {
          min: 0,
          max: modalData.rating_scale == 'graded' ? 4 : 1
        }
      }
      let response
      try {
        setLoadingModal(true)
        response = await api.create_project(doc)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to create project'
        }))
      } finally {
        setLoadingModal(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Created project',
        color: 'success',
        iconType: 'check',
        text: (
          <EuiText size='xs'>
            <b>{modalData.name}</b><br />
            <EuiText color='subdued' size='xs'>{response.data._id}</EuiText>
          </EuiText>
        )
      })

      // Redirect to scenarios on success
      window.location.href = `/#/projects/${response.data._id}/scenarios`
    })()
  }

  const onModalUpdateSubmit = async (e) => {
    e.preventDefault();
    (async () => {

      // Submit API request
      const doc = {
        name: modalData.name,
        indices: modalData.indices
      }
      let response
      try {
        setLoadingModal(true)
        response = await api.update_project(modalData._id, doc)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to update project'
        }))
      } finally {
        setLoadingModal(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Updated project',
        color: 'success',
        iconType: 'check',
        text: (
          <EuiText size='xs'>
            <b>{modalData.name}</b><br />
            <EuiText color='subdued' size='xs'>{modalData._id}</EuiText>
          </EuiText>
        )
      })
      setItems(prev => prev.map(item => item._id === modalData._id ? modalData : item))
      onModalUpdateClose()
    })()
  }

  const onModalDeleteSubmit = (e) => {
    e.preventDefault();
    (async () => {

      // Submit API request
      let response
      try {
        setLoadingModal(true)
        response = await api.delete_project(modalData._id)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to delete project'
        }))
      } finally {
        setLoadingModal(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Deleted project',
        color: 'success',
        iconType: 'check',
        text: (
          <EuiText size='xs'>
            <b>{modalData.name}</b><br />
            <EuiText color='subdued' size='xs'>{modalData._id}</EuiText>
          </EuiText>
        )
      })
      setItems(items.filter(item => item._id !== modalData._id))
      onModalDeleteClose()
    })()
  }


  ////  Handlers: Modal open and close  ////////////////////////////////////////

  const onModalCreateOpen = () => {
    setModalData({ name: '', indices: '', rating_scale: 'graded' })
    setModalCreateVisible(true)
  }

  const onModalUpdateOpen = (item) => {
    setModalData(item)
    setModalUpdateVisible(true)
  }

  const onModalDeleteOpen = (item) => {
    setModalData(item)
    setModalDeleteVisible(true)
  }

  const onModalCreateClose = () => {
    setModalData({})
    setModalCreateVisible(false)
  }

  const onModalUpdateClose = () => {
    setModalData({})
    setModalUpdateVisible(false)
  }

  const onModalDeleteClose = () => {
    setModalData({})
    setModalDeleteVisible(false)
  }


  ////  Elements: Modals  //////////////////////////////////////////////////////

  /**
   * Modal to create a projects.
   */
  const modalCreate = (
    <EuiModal onClose={onModalCreateClose}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          Create a new project
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiForm component='form' id='create'>
          <EuiFormRow label='Name' helpText='A descriptive name for this project.'>
            <EuiFieldText
              name='name'
              onChange={(e) => {
                setModalData(prev => ({ ...prev, name: e.target.value }))
              }}
              value={modalData.name}
            />
          </EuiFormRow>
          <EuiFormRow label='Indices' helpText={<>A comma-separated list of <a href='https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-multiple-data-streams-indices' target='_blank'>index patterns</a> to scope this set.</>}>
            <EuiFieldText
              name='indices'
              onChange={(e) => {
                setModalData(prev => ({ ...prev, indices: e.target.value, }))
              }}
              value={modalData.indices}
            />
          </EuiFormRow>
          <EuiFormRow label='Rating scale' helpText='All judgements in this set will conform to this rating scale.'>
            <EuiRadioGroup
              options={[
                {
                  id: 'graded',
                  label: <EuiFlexGroup>
                    <EuiFlexItem style={{ width: '65px' }}>
                      Graded
                    </EuiFlexItem>
                    <EuiFlexItem>
                      <EuiCode>0 - 4</EuiCode>
                    </EuiFlexItem>
                  </EuiFlexGroup>,
                },
                {
                  id: 'binary',
                  label: <EuiFlexGroup>
                    <EuiFlexItem style={{ width: '65px' }}>
                      Binary
                    </EuiFlexItem>
                    <EuiFlexItem>
                      <EuiCode>0 - 1</EuiCode>
                    </EuiFlexItem>
                  </EuiFlexGroup>,
                }
              ]}
              idSelected={modalData.rating_scale?.max == 1 ? 'binary' : 'graded'}
              onChange={(id) => {
                setModalData(prev => ({ ...prev, rating_scale: id }))
              }}
              name='rating_scale'
            />
          </EuiFormRow>
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          disabled={loadingModal || !(modalData.name || '').length || !(modalData.indices || '').length}
          fill
          form='create'
          isLoading={loadingModal}
          onClick={onModalCreateSubmit}
          type='submit'
        >
          Create
        </EuiButton>
        <EuiButton
          color='text'
          disabled={loadingModal}
          onClick={onModalCreateClose}
        >
          Cancel
        </EuiButton>
      </EuiModalFooter>
    </EuiModal>
  )

  /**
   * Modal to update a project.
   */
  const modalUpdate = (
    <EuiModal onClose={onModalUpdateClose}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          Update <b>{modalData.name}</b>
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiText color='subdued' size='xs'>Project _id:<br /><b>{modalData._id}</b></EuiText>
        <EuiSpacer size='m' />
        <EuiForm component='form' id='update'>
          <EuiFormRow label='Name' helpText='A descriptive name for this project.'>
            <EuiFieldText
              name='name'
              onChange={(e) => {
                setModalData(prev => ({ ...prev, name: e.target.value }))
              }}
              value={modalData.name}
            />
          </EuiFormRow>
          <EuiFormRow label='Indices' helpText={<>A comma-separated list of <a href='https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-multiple-data-streams-indices' target='_blank'>index patterns</a> to scope this set.</>}>
            <EuiFieldText
              name='indices'
              onChange={(e) => {
                setModalData(prev => ({ ...prev, indices: e.target.value, }))
              }}
              value={modalData.indices}
            />
          </EuiFormRow>
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          color='primary'
          disabled={loadingModal || !(modalData.name || '').length || !(modalData.indices || '').length}
          fill
          form='update'
          isLoading={loadingModal}
          onClick={onModalUpdateSubmit}
          type='submit'
        >
          Update
        </EuiButton>
        <EuiButton
          color='text'
          disabled={loadingModal}
          onClick={onModalUpdateClose}
        >
          Cancel
        </EuiButton>
      </EuiModalFooter>
    </EuiModal>
  )

  /**
   * Modal to delete a project.
   */
  const modalDelete = (
    <EuiModal onClose={onModalDeleteClose}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          Delete <b>{modalData.name}</b>?
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiForm component='form' id='delete'>
          <EuiText color='subdued' size='xs'>Project _id:<br /><b>{modalData._id}</b></EuiText>
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


  ////  Elements: Table  ///////////////////////////////////////////////////////

  const tableColumns = [
    {
      field: 'name',
      name: 'Name',
      sortable: true,
      truncateText: true,
      render: (name, item) => (<>{item.name}</>),
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
      name: 'Indices'
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
          name: 'delete',
          onClick: onModalUpdateOpen,
          type: 'icon',
        },
        {
          color: 'danger',
          description: 'Delete this project',
          icon: 'trash',
          name: 'delete',
          onClick: onModalDeleteOpen,
          type: 'icon',
        }
      ],
    }
  ]


  ////  Render  ////////////////////////////////////////////////////////////////

  /**
   * Button that opens the modal to create a project.
   */
  const buttonCreate = (
    <EuiButton
      fill
      iconType='plusInCircle'
      onClick={onModalCreateOpen}>
      Create a new project
    </EuiButton>
  )

  return (<>
    {modalCreateVisible && modalCreate}
    {modalUpdateVisible && modalUpdate}
    {modalDeleteVisible && modalDelete}
    <Page title='Projects' buttons={[buttonCreate]}>
      <EuiSkeletonText lines={10} isLoading={loadingItems}>
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
              onClick={onModalCreateOpen}>
              Create a new project
            </EuiButton>
          </EuiCallOut>
        }
        {!!items.length &&
          <EuiInMemoryTable
            responsiveBreakpoint={false}
            items={items}
            columns={tableColumns}
            pagination={true}
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