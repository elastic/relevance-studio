import React, { useEffect, useState } from 'react'
import { useHistory } from 'react-router-dom'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiCode,
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
  EuiPanel,
  EuiSkeletonText,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import Editor from '@monaco-editor/react'
import api from '../../api'
import utils from '../../utils'
import { Page } from '../../Layout'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'

const Scenarios = () => {

  const history = useHistory()

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, darkMode } = useAppContext()
  const { project, loadingProject } = useProjectContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [aggs, setAggs] = useState({})
  const [items, setItems] = useState([])
  const [loadingItems, setLoadingItems] = useState(true)
  const [loadingModal, setLoadingModal] = useState(false)
  const [modalData, setModalData] = useState({})
  const [modalCreateVisible, setModalCreateVisible] = useState(false)
  const [modalUpdateVisible, setModalUpdateVisible] = useState(false)
  const [modalDeleteVisible, setModalDeleteVisible] = useState(false)
  const [paramsDraft, setParamsDraft] = useState('')

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
        setLoadingItems(true)
        response = await api.get_scenarios(project._id)
      } catch (error) {
        return addToast(utils.toastClientError(error))
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
      response.data.aggregations.scenarios?.buckets.forEach(agg => {
        aggs[agg.key] = {
          ...aggs[agg.key] || {},
          judgements: agg.judgements.doc_count,
          evaluations: agg.evaluations.doc_count
        }
      })
      setAggs(aggs)
    })()
  }, [project])

  /**
   * Get params draft from scenario in modal
   */
  useEffect(() => {
    if (!modalData.params)
      return
    setParamsDraft(JSON.stringify(modalData.params, null, 2))
  }, [modalData.params])

  ////  Handlers: Modal submission  ////////////////////////////////////////////

  const onModalCreateSubmit = (e) => {
    e.preventDefault();
    (async () => {

      // Submit API request
      const paramsObj = JSON.parse(paramsDraft)
      const doc = { ...modalData, _id: undefined, params: paramsObj }
      let response
      try {
        setLoadingModal(true)
        response = await api.create_scenario(project._id, doc)
      } catch (error) {
        return addToast(utils.toastClientError(error))
      } finally {
        setLoadingModal(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Created scenario',
        color: 'success',
        iconType: 'check',
        text: (
          <EuiText size='xs'>
            <b>{modalData.name}</b><br />
            <EuiText color='subdued' size='xs'>{response.data._id}</EuiText>
          </EuiText>
        )
      })
      const item = { ...modalData, _id: response.data._id, params: paramsObj }
      setItems(prev => [...prev, item])
      onModalCreateClose()
    })()
  }

  const onModalUpdateSubmit = (e) => {
    e.preventDefault();
    (async () => {

      // Submit API request
      const doc = { ...modalData, _id: undefined, params: JSON.parse(paramsDraft) }
      let response
      try {
        setLoadingModal(true)
        response = await api.update_scenario(project._id, modalData._id, doc)
      } catch (error) {
        return addToast(utils.toastClientError(error))
      } finally {
        setLoadingModal(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Updated scenario',
        color: 'success',
        iconType: 'check',
        text: (
          <EuiText size='xs'>
            <b>{modalData.name}</b><br />
            <EuiText color='subdued' size='xs'>{modalData._id}</EuiText>
          </EuiText>
        )
      })
      const updatedItem = { ...modalData, params: JSON.parse(paramsDraft) }
      setItems(prev =>
        prev.map(item => item._id === modalData._id ? updatedItem : item)
      )
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
        response = await api.delete_scenario(project._id, modalData._id)
      } catch (error) {
        return addToast(utils.toastClientError(error))
      } finally {
        setLoadingModal(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Deleted scenario',
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
    setModalData({ name: '', params: { 'text': '' }, tags: [] })
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
    setParamsDraft('')
    setModalCreateVisible(false)
  }

  const onModalUpdateClose = () => {
    setModalData({})
    setParamsDraft('')
    setModalUpdateVisible(false)
  }

  const onModalDeleteClose = () => {
    setModalData({})
    setModalDeleteVisible(false)
  }

  const validParams = () => {
    try {
      JSON.parse(paramsDraft)
    } catch (e) {
      console.log(e)
      return false
    }
    return true
  }

  ////  Elements: Modals  //////////////////////////////////////////////////////

  const renderEditor = () => {
    return (
      <Editor
        defaultLanguage='json'
        height='100px'
        onChange={(value, event) => setParamsDraft(value)}
        options={{
          folding: false,
          fontSize: 10,
          glyphMargin: false,
          insertSpaces: true,
          lineDecorationsWidth: 0,
          lineNumbers: 'false',
          lineNumbersMinChars: 0,
          minimap: {
            enabled: false
          },
          renderLineHighlight: false,
          renderOverviewRuler: false,
          scrollBeyondLastLine: false,
          stickyScroll: {
            enabled: false,
          },
          tabSize: 2
        }}
        theme={darkMode ? 'vs-dark' : 'light'}
        value={paramsDraft}
      />
    )
  }

  /**
   * Modal to create a scenario.
   */
  const modalCreate = (
    <EuiModal onClose={onModalCreateClose}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          Create a new scenario
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiForm component='form' id='create'>
          <EuiFormRow label='Name' helpText='A descriptive name for this scenario.'>
            <EuiFieldText
              name='name'
              onChange={(e) => {
                setModalData(prev => ({ ...prev, name: e.target.value }))
              }}
              value={modalData.name}
            />
          </EuiFormRow>
          <EuiFormRow
            label='Params'
            helpText={<>
              <div>Values that will be passed to the params of strategies.</div>
              <div>Example: <EuiCode transparentBackground>{'{ "text": "brown shoes" }'}</EuiCode></div>
            </>}
          >
            <EuiPanel hasBorder paddingSize='s'>
              {renderEditor()}
            </EuiPanel>
          </EuiFormRow>
          <EuiFormRow label='Tags' helpText='Optional tags to keep things organized.'>
            <EuiComboBox
              noSuggestions
              placeholder='Tags'
              onChange={(options) => {
                const tags = []
                options.forEach((option) => tags.push(option.key))
                setModalData(prev => ({ ...prev, ['tags']: tags }))
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
          disabled={loadingModal || !(modalData.name || '').length || !validParams()}
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
   * Modal to update a scenario.
   */
  const modalUpdate = (
    <EuiModal onClose={onModalUpdateClose}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          Update <b>{modalData.name}</b>
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiText color='subdued' size='xs'>Scenario _id:<br /><b>{modalData._id}</b></EuiText>
        <EuiSpacer size='m' />
        <EuiForm component='form' id='update'>
          <EuiFormRow label='Name' helpText='A descriptive name for this scenario.'>
            <EuiFieldText
              name='name'
              onChange={(e) => {
                setModalData(prev => ({ ...prev, name: e.target.value }))
              }}
              value={modalData.name}
            />
          </EuiFormRow>
          <EuiFormRow
            label='Params'
            helpText={<>
              <div>Values that will be passed to the params of strategies.</div>
              <div>Example: <EuiCode transparentBackground>{'{ "text": "foobar" }'}</EuiCode></div>
            </>}
          >
            <EuiPanel hasBorder paddingSize='s'>
              {renderEditor()}
            </EuiPanel>
          </EuiFormRow>
          <EuiFormRow label='Tags' helpText='Optional tags to keep things organized.'>
            <EuiComboBox
              noSuggestions
              placeholder='Tags'
              onChange={(options) => {
                const tags = []
                options.forEach((option) => tags.push(option.key))
                setModalData(prev => ({ ...prev, ['tags']: tags }))
              }}
              onCreateOption={(tag) => {
                const tags = modalData.tags?.concat(tag)
                setModalData(prev => ({ ...prev, ['tags']: tags }))
              }}
              selectedOptions={(() => {
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
          disabled={loadingModal || !(modalData.name || '').length || !validParams()}
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
   * Modal to delete a scenario.
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
          <EuiText color='subdued' size='xs'>Scenario _id:<br /><b>{modalData._id}</b></EuiText>
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
                  scenario_id: item._id,
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
    {
      field: 'evaluations',
      name: 'Evaluations',
      render: (name, item) => {
        return (
          <EuiLink href={`#/projects/${project._id}/evaluations`}>
            {aggs[item._id]?.evaluations.toLocaleString() || 0}
          </EuiLink>
        )
      }
    },
    {
      field: 'params',
      name: 'Params',
      render: (name, item) => {
        const params = []
        for (var param in item.params)
          params.push(
            <EuiBadge color='hollow' key={param}>
              {param}: {item.params[param]}
            </EuiBadge>
          )
        if (!params.length)
          return <EuiBadge color='warning' iconType='warningFilled' size='xs'>none</EuiBadge>
        return params
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
          name: 'delete',
          onClick: onModalUpdateOpen,
          type: 'icon',
        },
        {
          color: 'danger',
          description: 'Delete this scenario',
          icon: 'trash',
          name: 'delete',
          onClick: onModalDeleteOpen,
          type: 'icon',
        }
      ],
    }
  ]

  /**
   * Button that opens the modal to create a scenarios.
   */
  const buttonCreate = (
    <EuiButton
      fill
      iconType='plusInCircle'
      onClick={onModalCreateOpen}>
      Create a new scenario
    </EuiButton>
  )

  return (<>
    {modalCreateVisible && modalCreate}
    {modalUpdateVisible && modalUpdate}
    {modalDeleteVisible && modalDelete}
    <Page title='Scenarios' buttons={[buttonCreate]}>
      <EuiSkeletonText lines={10} isLoading={loadingItems || loadingProject}>
        {!items.length &&
          <EuiCallOut
            color='primary'
            title='Welcome!'
          >
            <EuiText>
              Create your first scenario to get started.
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