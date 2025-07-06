import { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiFieldText,
  EuiForm,
  EuiFormRow,
  EuiIcon,
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

const Displays = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const history = getHistory()
  const { addToast } = useAppContext()
  const { project } = usePageResources()
  const isReady = useResources().hasResources(['project'])

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
  const [searchSortField, setSearchSortField] = useState("index_pattern")
  const [searchSortOrder, setSearchSortOrder] = useState("asc")
  const [searchText, setSearchText] = useState("")
  const [searchTotal, setSearchTotal] = useState(null)

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Automatically submit the search and return to page one either when the
   * project is ready or when the user changes pagination settings.
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
    searchFn: api.displays_search, // search displauy
    projectId: project?._id,
    searchText,
    searchPage,
    searchSize,
    searchSortField,
    searchSortOrder,
    useAggs: false, // displays don't have aggs
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
        response = await api.displays_create(project._id, doc)
      else if (action == 'update')
        response = await api.displays_update(project._id, _id, doc)
      else if (action == 'delete')
        response = await api.displays_delete(project._id, _id)
    } catch (e) {
      return addToast(api.errorToast(e, { title: `Failed to ${action} display` }))
    } finally {
      setIsProcessing(false)
    }
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    addToast(utils.toastDocCreateUpdateDelete(action, 'display', _id || response.data._id))

    if (modalCreate) {

      // Redirect to display editor
      history.push({ pathname: `/projects/${project._id}/displays/${response.data._id}` })
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
      doc.index_pattern = doc.index_pattern.trim()
      return await onSubmitModal('create', doc)

    } else if (modalUpdate) {
      // Prepare doc field updates
      const doc = {
        index_pattern: modalUpdate.index_pattern.trim(),
        template: modalUpdate.template
      }
      return await onSubmitModal('update', doc, modalUpdate._id)
    }
  }

  /**
   * Check if the index pattern of the display is within the scope of the
   * index pattern of the project. Both can have commas, so those are split,
   * and if any of the input splits matches any of the target splits,
   * then consider the whole thing to be a match.
   */
  const isIndexPatternInProjectScope = (inputPattern, targetPattern) => {
    const toParts = (pattern) => pattern.split(',').map(p => p.trim()).filter(Boolean)
    const toRegex = (glob) => new RegExp('^' + glob.replace(/[-[\]/{}()+?.\\^$|]/g, '\\$&').replace(/\*/g, '.*') + '$')
    const inputs = toParts(inputPattern)
    const targets = toParts(targetPattern)
    return inputs.some(input =>
      targets.some(target =>
        toRegex(target).test(input) || toRegex(input).test(target)
      )
    )
  }

  const indexPatternInput = (modalCreate?.index_pattern || modalUpdate?.index_pattern) || ''
  const indexPatternInScope = project ? isIndexPatternInProjectScope(indexPatternInput, project.index_pattern) : false

  ////  Render  ////////////////////////////////////////////////////////////////

  const columns = [
    {
      field: 'index_pattern',
      name: 'Index Pattern',
      sortable: true,
      truncateText: true,
      render: (name, doc) => {
        return <EuiLink href={`#/projects/${project._id}/displays/${doc._id}`}>
          {doc.index_pattern}
        </EuiLink>
      }
    },
    {
      field: 'fields',
      width: '100px',
      name: 'Fields',
      render: (name, doc) => {
        const fields = []
        for (var i in doc.fields)
          fields.push(
            <EuiBadge color='hollow' key={doc.fields[i]}>
              {doc.fields[i]}
            </EuiBadge>
          )
        if (!fields.length)
          return <EuiBadge color='warning' iconType='warningFilled' size='xs'>none</EuiBadge>
        return fields
      },
    },
    {
      name: 'Actions',
      width: '100px',
      actions: [
        {
          color: 'text',
          description: 'Update this display',
          icon: 'documentEdit',
          name: 'update',
          onClick: (doc) => setModalUpdate(doc),
          type: 'icon',
        },
        {
          color: 'danger',
          description: 'Delete this display',
          icon: 'trash',
          name: 'delete',
          onClick: (doc) => setModalDelete(doc),
          type: 'icon',
        }
      ],
    }
  ]

  /**
   * Modal to create or update a display.
   */
  const renderModalCreateUpdate = () => (
    <EuiModal onClose={() => { setModalCreate(null); setModalUpdate(null) }}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          {modalCreate ? 'Create a new display' : 'Update display'}
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiForm component='form' id='create-update'>
          <EuiFormRow label='Index Pattern' helpText={<>
            <p>
              An <a href='https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-multiple-data-streams-indices' target='_blank'>index pattern</a> whose documents will render with this display.<br />It must be a subset of this project's index pattern.
            </p>
            <br />
            <p>
              Project index pattern: <b>{project?.index_pattern}</b>
            </p>
            <br />
            {indexPatternInput.trim() == '' &&
              <p><small>&nbsp;</small></p>
            }
            {indexPatternInput.trim() != '' &&
              <p>
                <EuiIcon
                  color={indexPatternInScope ? 'success' : 'danger'}
                  size='s'
                  style={{ marginRight: '10px' }}
                  type={indexPatternInScope ? 'check' : 'cross'}
                />
                <small>
                  Your display's index pattern is {indexPatternInScope ? '' : 'not'} within the scope of the project.
                </small>
              </p>
            }
          </>}>
            <EuiFieldText
              name='name'
              onChange={(e) => {
                if (modalCreate)
                  return setModalCreate(prev => ({ ...prev, index_pattern: e.target.value }))
                return setModalUpdate(prev => ({ ...prev, index_pattern: e.target.value }))
              }}
              value={(() => {
                return modalCreate ? modalCreate.index_pattern : modalUpdate.index_pattern
              })()}
            />
          </EuiFormRow>
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          disabled={isProcessing || !indexPatternInput.trim().length || !indexPatternInScope}
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
      docType='display'
      isProcessing={isProcessing}
      onClose={() => setModalDelete(null)}
      onDelete={async () => await api.displays_delete(project._id, modalDelete._id)}
      onSuccess={onSubmitSearch}
      setIsProcessing={setIsProcessing}
    />
  )

  /**
   * Button that opens the modal to create a display.
   */
  const renderButtonCreate = () => (
    <EuiButton
      fill
      iconType='plusInCircle'
      onClick={() => setModalCreate({ index_pattern: '', template: { body: '' } })}>
      Create a new display
    </EuiButton>
  )

  return (
    <Page title='Displays' buttons={[renderButtonCreate()]}>
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
                Create your first display to get started.
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

export default Displays