import { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiLink,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import { useSearchHandler } from '../../Hooks'
import { ModalDelete, Page, SearchTable } from '../../Layout'
import FlyoutForm from './FlyoutForm'
import { getHistory } from '../../history'
import api from '../../api'

const Workspaces = () => {

  const history = getHistory()

  ////  State  /////////////////////////////////////////////////////////////////

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
  const [searchAggs, setSearchAggs] = useState({})
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
    onSubmitSearch()
    setSearchPage(1)
  }, [searchSize, searchSortField, searchSortOrder])

  /**
   * Automatically submit the search when the user selects a different page in
   * the search results.
   */
  useEffect(() => {
    onSubmitSearch()
  }, [searchPage])

  /**
   * Search handler
   */
  const onSubmitSearch = useSearchHandler({
    searchFn: api.workspaces_search, // search workspaces
    searchText,
    searchPage,
    searchSize,
    searchSortField,
    searchSortOrder,
    useAggs: true, // workspaces have aggs
    setDocs: setSearchDocs,
    setAggs: setSearchAggs,
    setTotal: setSearchTotal,
    setLoading: setIsSearchLoading,
    setHasEverSearched: setHasEverSearched,
    setIsIndexEmpty: setIsIndexEmpty,
  })

  ////  Render  ////////////////////////////////////////////////////////////////

  const columns = [
    {
      field: 'name',
      name: 'Name',
      sortable: true,
      truncateText: true,
      render: (name, doc) => (
        <EuiLink href={`#/workspaces/${doc._id}`}>
          <EuiButton fill iconSize='s' iconType='folderOpen' size='s'>
            <small>{doc.name}</small>
          </EuiButton>
        </EuiLink>
      ),
    },
    {
      field: 'scenarios',
      name: 'Scenarios',
      sortable: true,
      render: (name, doc) => (
        <EuiLink href={`#/workspaces/${doc._id}/scenarios`}>
          {searchAggs[doc._id]?.scenarios.toLocaleString() || 0}
        </EuiLink>
      ),
    },
    {
      field: 'judgements',
      name: 'Judgements',
      sortable: true,
      render: (name, doc) => (
        <EuiLink href={`#/workspaces/${doc._id}/judgements`}>
          {searchAggs[doc._id]?.judgements.toLocaleString() || 0}
        </EuiLink>
      ),
    },
    {
      field: 'strategies',
      name: 'Strategies',
      sortable: true,
      render: (name, doc) => (
        <EuiLink href={`#/workspaces/${doc._id}/strategies`}>
          {searchAggs[doc._id]?.strategies.toLocaleString() || 0}
        </EuiLink>
      ),
    },
    {
      field: 'benchmarks',
      name: 'Benchmarks',
      sortable: true,
      render: (name, doc) => (
        <EuiLink href={`#/workspaces/${doc._id}/benchmarks`}>
          {searchAggs[doc._id]?.benchmarks.toLocaleString() || 0}
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
        {doc.rating_scale.min} <span style={{ fontSize: '10px', padding: '0 4px' }}>{'-->'}</span> {doc.rating_scale.max}
      </>),
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
      name: 'Actions',
      actions: [
        {
          color: 'text',
          description: 'Manage displays',
          icon: 'palette',
          isPrimary: true,
          name: 'Displays',
          onClick: (doc) => {
            history.push({ pathname: `/workspaces/${doc._id}/displays` })
          },
          type: 'icon'
        },
        {
          color: 'text',
          description: 'Update this workspace',
          icon: 'documentEdit',
          isPrimary: true,
          name: 'Update',
          onClick: (doc) => setFlyout(doc),
          type: 'icon',
        },
        {
          color: 'danger',
          description: 'Delete this workspace',
          icon: 'trash',
          name: 'Delete',
          onClick: (doc) => setModalDelete(doc),
          type: 'icon',
        }
      ],
    }
  ]


  ////  Render  ////////////////////////////////////////////////////////////////

  const renderFlyout = () => (
    <FlyoutForm
      action={flyout === true ? 'create' : 'update'}
      doc={flyout}
      isProcessing={isProcessing}
      onClose={() => setFlyout(null)}
      onSuccess={(_id) => {
        if (flyout === true) {
          // Redirect to workspace on create
          history.push({ pathname: `/workspaces/${_id}` })
        } else {
          // Refresh table on update
          onSubmitSearch()
        }
      }}
      setIsProcessing={setIsProcessing}
    />
  )

  const renderModalDelete = () => (
    <ModalDelete
      description={
        !!Object.keys((searchAggs[modalDelete._id]) || {}).length &&
        <EuiText>
          <p>This will delete all assets related to this workspace:</p>
          <ul>
            {!!searchAggs[modalDelete._id]?.displays &&
              <li>{searchAggs[modalDelete._id]?.displays || 0} display{searchAggs[modalDelete._id]?.displays == 1 ? '' : 's'}</li>
            }
            {!!searchAggs[modalDelete._id]?.scenarios &&
              <li>{searchAggs[modalDelete._id]?.scenarios || 0} scenario{searchAggs[modalDelete._id]?.scenarios == 1 ? '' : 's'}</li>
            }
            {!!searchAggs[modalDelete._id]?.judgements &&
              <li>{searchAggs[modalDelete._id]?.judgements || 0} judgement{searchAggs[modalDelete._id]?.judgements == 1 ? '' : 's'}</li>
            }
            {!!searchAggs[modalDelete._id]?.strategies &&
              <li>{searchAggs[modalDelete._id]?.strategies || 0} {searchAggs[modalDelete._id]?.strategies == 1 ? 'strategy' : 'strategies'}</li>
            }
            {!!searchAggs[modalDelete._id]?.evaluations &&
              <li>{searchAggs[modalDelete._id]?.evaluations || 0} evaluation{searchAggs[modalDelete._id]?.evaluations == 1 ? '' : 's'}</li>
            }
          </ul>
        </EuiText>
      }
      doc={modalDelete}
      docType='workspace'
      isLoading={isProcessing}
      onClose={() => setModalDelete(null)}
      //onError={(e) => addToast(api.errorToast(e, { title: `Failed to delete workspace` }))}
      onDelete={async () => await api.workspaces_delete(modalDelete._id)}
      onSuccess={onSubmitSearch}
      setIsProcessing={setIsProcessing}
    />
  )

  const renderButtonCreate = () => (
    <EuiButton fill iconType='plusInCircle' onClick={() => setFlyout(true)}>
      Create a new workspace
    </EuiButton>
  )

  return (
    <Page title='Workspaces' buttons={[renderButtonCreate()]}>
      {modalDelete && renderModalDelete()}
      {flyout && renderFlyout()}
      {hasEverSearched &&
        <>
          {isIndexEmpty &&
            <EuiCallOut
              color='primary'
              title='Welcome!'
            >
              <EuiText>
                Create your first workspace to get started.
              </EuiText>
              <EuiSpacer size='m' />
              <EuiButton
                fill
                iconType='plusInCircle'
                onClick={() => setFlyout(true)}>
                Create a new workspace
              </EuiButton>
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

export default Workspaces