/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiComboBox,
  EuiFieldText,
  EuiForm,
  EuiFormRow,
  EuiLink,
  EuiModal,
  EuiModalHeaderTitle,
  EuiModalBody,
  EuiModalFooter,
  EuiModalHeader,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { usePageResources, useResources } from '../../Contexts/ResourceContext'
import { useSearchHandler } from '../../Hooks'
import { ModalDelete, Page, SearchTable } from '../../Layout'
import { getHistory } from '../../history'
import api from '../../api'
import utils from '../../utils'

const Strategies = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const history = getHistory()
  const { addToast } = useAppContext()
  const { workspace } = usePageResources()
  const isReady = useResources().hasResources(['workspace'])

  ////  State  /////////////////////////////////////////////////////////////////

  /**
   * null:   close modal
   * true:   open modal to create a new doc
   */
  const [modalCreate, setModalCreate] = useState(null)

  /**
   * null:   close modal
   * object: open modal to update a given doc (object)
   */
  const [modalUpdate, setModalUpdate] = useState(null)

  /**
   * null:   close modal
   * object: open modal to delete a given doc (object)
   */
  const [modalDelete, setModalDelete] = useState(null)

  /**
   * Whether a doc is being updated or deleted
   */
  const [isProcessing, setIsProcessing] = useState(false)

  /**
   * Search state
   */
  const [hasEverSearched, setHasEverSearched] = useState(false)
  const [isIndexEmpty, setIsIndexEmpty] = useState(null)
  const [isSearchLoading, setIsSearchLoading] = useState(false)
  const [searchDocs, setSearchDocs] = useState([])
  const [searchPage, setSearchPage] = useState(1)
  const [searchSize, setSearchSize] = useState(10)
  const [searchSortField, setSearchSortField] = useState("name")
  const [searchSortOrder, setSearchSortOrder] = useState("asc")
  const [searchText, setSearchText] = useState("")
  const [searchTotal, setSearchTotal] = useState(null)

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Automatically submit the search and return to page one either when the
   * workspace is ready or when the user changes pagination settings.
   */
  useEffect(() => {
    if (!isReady)
      return
    onSubmitSearch()
    setSearchPage(1)
  }, [isReady, searchSize, searchSortField, searchSortOrder])

  /**
   * Automatically submit the search when the user selects a different page in
   * the search results.
   */
  useEffect(() => {
    if (!isReady)
      return
    onSubmitSearch()
  }, [searchPage])

  /**
   * Search handler
   */
  const onSubmitSearch = useSearchHandler({
    searchFn: api.strategies_search, // search strategies
    workspaceId: workspace?._id,
    searchText,
    searchPage,
    searchSize,
    searchSortField,
    searchSortOrder,
    useAggs: false, // strategies don't have aggs
    setDocs: setSearchDocs,
    setTotal: setSearchTotal,
    setLoading: setIsSearchLoading,
    setHasEverSearched: setHasEverSearched,
    setIsIndexEmpty: setIsIndexEmpty,
  })

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onSubmitModal = async (action, doc, _id) => {
    let response
    try {
      setIsProcessing(true)
      if (action == 'create')
        response = await api.strategies_create(workspace._id, doc)
      else if (action == 'update')
        response = await api.strategies_update(workspace._id, _id, doc)
      else if (action == 'delete')
        response = await api.strategies_delete(workspace._id, _id)
    } catch (e) {
      return addToast(api.errorToast(e, { title: `Failed to ${action} strategy` }))
    } finally {
      setIsProcessing(false)
    }
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    addToast(utils.toastDocCreateUpdateDelete(action, 'strategy', _id || response.data._id))

    if (modalCreate) {

      // Redirect to strategy editor
      history.push({ pathname: `/workspaces/${workspace._id}/strategies/${response.data._id}` })
      return setModalCreate(null)
    } else {

      // Reload table and close modal
      setModalUpdate(null)
      onSubmitSearch()
      setSearchPage(1)
    }
  }

  const onSubmitModalCreateUpdate = async (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();

    if (modalCreate) {
      // Prepare doc
      const doc = { ...modalCreate }
      doc.name = doc.name.trim()
      return await onSubmitModal('create', doc)

    } else if (modalUpdate) {
      // Prepare doc field updates
      // Pass whole doc, because index() is required for updates to strategies.
      const doc = { ...modalUpdate }
      doc.name = modalUpdate.name.trim()
      doc.tags = modalUpdate.tags || []
      delete doc.params // delete immutable fields if they exist
      return await onSubmitModal('update', doc, modalUpdate._id)
    }
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const columns = [
    {
      field: 'name',
      name: 'Strategy',
      sortable: true,
      truncateText: true,
      render: (name, doc) => (
        <EuiLink href={`#/workspaces/${workspace._id}/strategies/${doc._id}`}>
          {doc.name}
        </EuiLink>
      )
    },
    {
      field: 'tags',
      name: 'Tags',
      width: '100px',
      render: (name, doc) => {
        const tags = []
        for (var i in doc.tags)
          tags.push(
            <EuiBadge color='hollow' key={doc.tags[i]}>
              {doc.tags[i]}
            </EuiBadge>
          )
        return tags
      },
    },
    {
      field: 'params',
      name: 'Params',
      width: '100px',
      render: (name, doc) => {
        const params = []
        for (var i in doc.params)
          params.push(
            <EuiBadge color='hollow' key={doc.params[i]}>
              {doc.params[i]}
            </EuiBadge>
          )
        if (!params.length)
          return <EuiBadge color='warning' iconType='warningFilled' size='xs'>none</EuiBadge>
        return params
      },
    },
    {
      name: 'Actions',
      width: '100px',
      actions: [
        {
          color: 'text',
          description: 'Update this strategy',
          icon: 'documentEdit',
          name: 'update',
          onClick: (doc) => setModalUpdate(doc),
          type: 'icon',
        },
        {
          color: 'danger',
          description: 'Delete this strategy',
          icon: 'trash',
          name: 'delete',
          onClick: (doc) => setModalDelete(doc),
          type: 'icon',
        }
      ],
    }
  ]

  /**
   * Modal to create or update a strategy.
   */
  const renderModalCreateUpdate = () => (
    <EuiModal onClose={() => { setModalCreate(null); setModalUpdate(null) }}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          {modalCreate ? 'Create a new strategy' : 'Update strategy'}
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiForm component='form' id='create-update'>
          <EuiFormRow label='Name' helpText='A descriptive name for this strategy.'>
            <EuiFieldText
              name='name'
              onChange={(e) => {
                if (modalCreate)
                  return setModalCreate(prev => ({ ...prev, name: e.target.value }))
                return setModalUpdate(prev => ({ ...prev, name: e.target.value }))
              }}
              value={(() => {
                return modalCreate ? modalCreate.name : modalUpdate.name
              })()}
            />
          </EuiFormRow>
          <EuiFormRow label='Tags' helpText='Optional tags to keep things organized.'>
            <EuiComboBox
              noSuggestions
              placeholder='Tags'
              onChange={(options) => {
                const tags = []
                options.forEach((option) => tags.push(option.key))
                if (modalCreate)
                  return setModalCreate(prev => ({ ...prev, ['tags']: tags }))
                return setModalUpdate(prev => ({ ...prev, ['tags']: tags }))
              }}
              onCreateOption={(tag) => {
                const currentTags = (modalCreate || modalUpdate).tags || []
                const tags = [...currentTags, tag]
                if (modalCreate)
                  return setModalCreate(prev => ({ ...prev, tags }))
                return setModalUpdate(prev => ({ ...prev, tags }))
              }}
              selectedOptions={(modalCreate || modalUpdate).tags?.map((tag) => ({ key: tag, label: tag }))}
            />
          </EuiFormRow>
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          disabled={isProcessing || !((modalCreate || modalUpdate).name || '').length}
          fill
          form='create-update'
          isLoading={isProcessing}
          onClick={onSubmitModalCreateUpdate}
          type='submit'
        >
          {modalCreate ? 'Create' : 'Update'}
        </EuiButton>
        <EuiButton
          color='text'
          disabled={isProcessing}
          onClick={() => { setModalCreate(null); setModalUpdate(null) }}
        >
          Cancel
        </EuiButton>
      </EuiModalFooter>
    </EuiModal>
  )

  const renderModalDelete = () => (
    <ModalDelete
      doc={modalDelete}
      docType='strategy'
      isProcessing={isProcessing}
      onClose={() => setModalDelete(null)}
      onDelete={async () => await api.strategies_delete(workspace._id, modalDelete._id)}
      onSuccess={onSubmitSearch}
      setIsProcessing={setIsProcessing}
    />
  )

  const renderButtonCreate = () => (
    <EuiButton fill iconType='plusInCircle' onClick={() => setModalCreate({
      name: '',
      tags: [],
      template: {
        lang: 'mustache',
        source: '{}'
      }
    })}>
      Create a new strategy
    </EuiButton>
  )

  return (
    <Page title='Strategies' buttons={[renderButtonCreate()]}>
      {(modalCreate || modalUpdate) && renderModalCreateUpdate()}
      {modalDelete && renderModalDelete()}
      {hasEverSearched &&
        <>
          {isIndexEmpty &&
            <EuiCallOut
              color='primary'
              title='Welcome!'
            >
              <EuiText>
                Create your first strategy to get started.
              </EuiText>
              <EuiSpacer size='m' />
              {renderButtonCreate()}
            </EuiCallOut>
          }
          {isIndexEmpty === false &&
            <SearchTable
              docs={searchDocs}
              total={searchTotal}
              page={searchPage}
              size={searchSize}
              sortField={searchSortField}
              sortOrder={searchSortOrder}
              isLoading={isSearchLoading}
              columns={columns}
              searchText={searchText}
              onChangeText={setSearchText}
              onChangePage={setSearchPage}
              onChangeSize={setSearchSize}
              onChangeSort={(field, order) => {
                setSearchSortField(field)
                setSearchSortOrder(order)
              }}
              onSubmit={() => {
                onSubmitSearch()
                setSearchPage(1)
              }}
            />
          }
        </>
      }
    </Page>
  )
}

export default Strategies