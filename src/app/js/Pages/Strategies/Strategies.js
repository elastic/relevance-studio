import React, { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiComboBox,
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

const Strategies = () => {

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
   * Get strategies on load
   */
  useEffect(() => {
    if (!project?._id)
      return
    (async () => {
    
      // Submit API request
      let response
      try {
        setLoadingItems(true)
        response = await api.get_strategies(project._id)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to get strategies'
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
        response = await api.create_strategy(project._id, doc)
      } catch (error) {
        return addToast(utils.toastClientError(error))
      } finally {
        setLoadingModal(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Created strategy',
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
      window.location.href = `/#/projects/${project._id}/strategies/${response.data._id}`
    })()
  }

  const onModalUpdateSubmit = (e) => {
    e.preventDefault();
    (async () => {
    
      // Submit API request
      const doc = {
        name: modalData.name,
        params: modalData.params,
        tags: modalData.tags,
        template: modalData.template
      }
      let response
      try {
        setLoadingModal(true)
        response = await api.update_strategy(project._id, modalData._id, doc)
      } catch (error) {
        return addToast(utils.toastClientError(error))
      } finally {
        setLoadingModal(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Updated strategy',
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
        response = await api.delete_strategy(project._id, modalData._id)
      } catch (error) {
        return addToast(utils.toastClientError(error))
      } finally {
        setLoadingModal(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Deleted strategy',
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
    setModalData({ name: '', params: [], tags: [], template: { source: {}}})
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
   * Modal to create a strategy.
   */
  const modalCreate = (
    <EuiModal onClose={onModalCreateClose}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          Create a new strategy
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiForm component='form' id='create'>
          <EuiFormRow label='Name' helpText='A descriptive name for this strategy.'>
            <EuiFieldText
              name='name'
              onChange={(e) => {
                setModalData(prev => ({ ...prev, name: e.target.value }))
              }}
              value={modalData.name}
            />
          </EuiFormRow>
          <EuiFormRow label='Tags' helpText='Optional tags to keep things organized.'>
            <EuiComboBox
              noSuggestions
              placeholder='Tags'
              onChange={(options) => {
                const tags = []
                options.forEach((option) => tags.push(option.key))
                setModalData(prev => ({...prev, ['tags']: tags }))
              }}
              onCreateOption={(tag) => {
                const tags = modalData.tags?.concat(tag)
                setModalData(prev => ({ ...prev, ['tags']: tags }))
              }}
              selectedOptions={modalData.tags?.map((tag) => ({ key: tag, label: tag }))}
            />
          </EuiFormRow>
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          disabled={loadingModal || !(modalData.name || '').length}
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
   * Modal to update a strategy.
   */
  const modalUpdate = (
    <EuiModal onClose={onModalUpdateClose}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          Update <b>{modalData.name}</b>
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiText color='subdued' size='xs'>Strategy _id:<br /><b>{modalData._id}</b></EuiText>
        <EuiSpacer size='m' />
        <EuiForm component='form' id='update'>
          <EuiFormRow label='Name' helpText='A descriptive name for this strategy.'>
            <EuiFieldText
              name='name'
              onChange={(e) => {
                setModalData(prev => ({ ...prev, name: e.target.value }))
              }}
              value={modalData.name}
            />
          </EuiFormRow>
          <EuiFormRow label='Tags' helpText='Optional tags to keep things organized.'>
            <EuiComboBox
              noSuggestions
              placeholder='Tags'
              onChange={(options) => {
                const tags = []
                options.forEach((option) => tags.push(option.key))
                setModalData(prev => ({...prev, ['tags']: tags }))
              }}
              onCreateOption={(tag) => {
                const tags = modalData.tags?.concat(tag)
                setModalData(prev => ({ ...prev, ['tags']: tags }))
              }}
              selectedOptions={(()=> {
                const options = []
                modalData.tags?.forEach((tag) => options.push({
                  key: tag,
                  label: tag
                }))
                return options
              })()}
            />
          </EuiFormRow>
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          color='primary'
          disabled={loadingModal || !(modalData.name || '').length}
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
   * Modal to delete a strategy.
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
          <EuiText color='subdued' size='xs'>Strategy _id:<br /><b>{modalData._id}</b></EuiText>
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
      field: 'name',
      name: 'Strategy',
      sortable: true,
      truncateText: true,
      render: (name, item) => (
        <EuiLink href={`#/projects/${project._id}/strategies/${item._id}`}>
          {item.name}
        </EuiLink>
      )
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
      field: 'params',
      name: 'Params',
      render: (name, item) => {
        const params = []
        for (var i in item.params)
          params.push(
            <EuiBadge color='hollow' key={item.params[i]}>
              {item.params[i]}
            </EuiBadge>
          )
        if (!params.length)
          return <EuiBadge color='warning' iconType='warningFilled' size='xs'>none</EuiBadge>
        return params
      },
    },
    {
      name: 'Actions',
      actions: [
        {
          color: 'text',
          description: 'Update this strategy',
          icon: 'documentEdit',
          name: 'delete',
          onClick: onModalUpdateOpen,
          type: 'icon',
        },
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
   * Button that opens the modal to create a strategy.
   */
  const buttonCreate = (
    <EuiButton
      fill
      iconType='plusInCircle'
      onClick={onModalCreateOpen}>
      Create a new strategy
    </EuiButton>
  )

  return (<>
      {modalCreateVisible && modalCreate}
      {modalUpdateVisible && modalUpdate}
      {modalDeleteVisible && modalDelete}
      <Page title='Strategies' buttons={[buttonCreate]}>
        <EuiSkeletonText lines={10} isLoading={loadingItems || loadingProject}>
          { !items.length &&
          <EuiCallOut
            color='primary'
            title='Welcome!'
          >
            <EuiText>
              Create your first strategy to get started.
            </EuiText>
            <EuiSpacer size='m' />
            {buttonCreate}
          </EuiCallOut>
          }
          { !!items.length &&
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
 
export default Strategies