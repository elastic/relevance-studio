import React, { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiFieldText,
  EuiForm,
  EuiFormRow,
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

const Displays = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const { project, loadingProject } = useProjectContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [items, setItems] = useState([])
  const [loadingItems, setLoadingItems] = useState(true)
  const [loadingModal, setLoadingModal] = useState(false)
  const [modalData, setModalData] = useState({})
  const [modalCreateVisible, setModalCreateVisible] = useState(false)
  const [modalUpdateVisible, setModalUpdateVisible] = useState(false)
  const [modalDeleteVisible, setModalDeleteVisible] = useState(false)

  /**
   * Get displays on load
   */
  useEffect(() => {
    if (!project?._id)
      return
    (async () => {

      // Submit API request
      let response
      try {
        setLoadingItems(true)
        response = await api.get_displays(project._id)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to get displays'
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

  ////  Handlers: Modal submission  ////////////////////////////////////////////

  const onModalCreateSubmit = (e) => {
    e.preventDefault();
    (async () => {

      // Submit API request
      const doc = { ...modalData }
      let response
      try {
        setLoadingModal(true)
        response = await api.create_display(project._id, doc)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to create display'
        }))
      } finally {
        setLoadingModal(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Created display',
        color: 'success',
        iconType: 'check',
        text: (
          <EuiText size='xs'>
            <b>{modalData.name}</b><br />
            <EuiText color='subdued' size='xs'>{response.data._id}</EuiText>
          </EuiText>
        )
      })

      // Redirect on success
      window.location.href = `/#/projects/${project._id}/displays/${response.data._id}`
    })()
  }

  const onModalUpdateSubmit = (e) => {
    e.preventDefault();
    (async () => {

      // Submit API request
      const doc = {
        index_pattern: modalData.index_pattern,
        template: modalData.template
      }
      let response
      try {
        setLoadingModal(true)
        response = await api.update_display(project._id, modalData._id, doc)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to update display'
        }))
      } finally {
        setLoadingModal(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Updated display',
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
        response = await api.delete_display(project._id, modalData._id)
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
        title: 'Deleted display',
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
    setModalData({ index_pattern: '', template: { body: {} } })
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
   * Modal to create a display.
   */
  const modalCreate = (
    <EuiModal onClose={onModalCreateClose}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          Create a new display
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiForm component='form' id='create'>
          <EuiFormRow label='Index Pattern' helpText={<>An <a href='https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-multiple-data-streams-indices' target='_blank'>index pattern</a> that applies to this display.</>}>
            <EuiFieldText
              name='name'
              onChange={(e) => {
                setModalData(prev => ({ ...prev, index_pattern: e.target.value }))
              }}
              value={modalData.index_pattern}
            />
          </EuiFormRow>
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          disabled={loadingModal || !(modalData.index_pattern || '').length}
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
   * Modal to update a display.
   */
  const modalUpdate = (
    <EuiModal onClose={onModalUpdateClose}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          Update display: <b>{modalData._id}</b>
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiText color='subdued' size='xs'>Display _id:<br /><b>{modalData._id}</b></EuiText>
        <EuiSpacer size='m' />
        <EuiForm component='form' id='update'>
          <EuiFormRow label='Index Pattern' helpText={<>An <a href='https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-multiple-data-streams-indices' target='_blank'>index pattern</a> that applies to this display.</>}>
            <EuiFieldText
              name='name'
              onChange={(e) => {
                setModalData(prev => ({ ...prev, index_pattern: e.target.value }))
              }}
              value={modalData.index_pattern}
            />
          </EuiFormRow>
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          color='primary'
          disabled={loadingModal || !(modalData.index_pattern || '').length}
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
   * Modal to delete a display.
   */
  const modalDelete = (
    <EuiModal onClose={onModalDeleteClose}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          Delete display for {modalData.index_pattern}
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiForm component='form' id='delete'>
          <EuiText color='subdued' size='xs'>Display _id:<br /><b>{modalData._id}</b></EuiText>
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

  const tableColumns = () => [
    {
      field: 'name',
      name: 'Index Pattern',
      sortable: true,
      truncateText: true,
      render: (name, item) => {
        return <EuiLink href={`#/projects/${project._id}/displays/${item._id}`}>
          {item.index_pattern}
        </EuiLink>
      }
    },
    {
      field: 'fields',
      name: 'Fields',
      render: (name, item) => {
        const fields = []
        for (var i in item.fields)
          fields.push(
            <EuiBadge color='hollow' key={item.fields[i]}>
              {item.fields[i]}
            </EuiBadge>
          )
        if (!fields.length)
          return <EuiBadge color='warning' iconType='warningFilled' size='xs'>none</EuiBadge>
        return fields
      },
    },
    {
      name: 'Actions',
      actions: [
        {
          color: 'text',
          description: 'Update this display',
          icon: 'documentEdit',
          name: 'delete',
          onClick: onModalUpdateOpen,
          type: 'icon',
        },
        {
          color: 'danger',
          description: 'Delete this display',
          icon: 'trash',
          name: 'delete',
          onClick: onModalDeleteOpen,
          type: 'icon',
        }
      ],
    }
  ]

  /**
   * Button that opens the modal to create a display.
   */
  const buttonCreate = (
    <EuiButton
      fill
      iconType='plusInCircle'
      onClick={onModalCreateOpen}>
      Create a new display
    </EuiButton>
  )

  return (<>
    {!loadingProject &&
      <>
        {modalCreateVisible && modalCreate}
        {modalUpdateVisible && modalUpdate}
        {modalDeleteVisible && modalDelete}
      </>
    }
    <Page title='Displays' buttons={[buttonCreate]}>
      <EuiSkeletonText lines={10} isLoading={loadingItems || loadingProject}>
        {!items.length &&
          <EuiCallOut
            color='primary'
            title='Welcome!'
          >
            <EuiText>
              Create your first display to get started.
            </EuiText>
            <EuiSpacer size='m' />
            {buttonCreate}
          </EuiCallOut>
        }
        {!!items.length &&
          <EuiInMemoryTable
            columns={tableColumns()}
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

export default Displays