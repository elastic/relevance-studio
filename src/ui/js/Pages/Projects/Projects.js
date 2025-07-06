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

const Projects = () => {

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
   * Mode detection
   */
  const [mode, setMode] = useState(null)

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
   * Load mode information on component mount
   */
  useEffect(() => {
    const loadMode = async () => {
      try {
        const response = await api.mode_get()
        setMode(response.data.mode)
      } catch (e) {
        console.error('Failed to load mode:', e)
        setMode('unknown')
      }
    }
    loadMode()
  }, [])

  /**
   * Automatically submit the search and return to page one either when the
   * project is ready or when the user changes pagination settings.
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
    searchFn: api.projects_search, // search projects
    searchText,
    searchPage,
    searchSize,
    searchSortField,
    searchSortOrder,
    useAggs: true, // projects have aggs
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
        <EuiLink href={`#/projects/${doc._id}`}>
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
        <EuiLink href={`#/projects/${doc._id}/scenarios`}>
          {searchAggs[doc._id]?.scenarios.toLocaleString() || 0}
        </EuiLink>
      ),
    },
    {
      field: 'judgements',
      name: 'Judgements',
      sortable: true,
      render: (name, doc) => (
        <EuiLink href={`#/projects/${doc._id}/judgements`}>
          {searchAggs[doc._id]?.judgements.toLocaleString() || 0}
        </EuiLink>
      ),
    },
    {
      field: 'strategies',
      name: 'Strategies',
      sortable: true,
      render: (name, doc) => (
        <EuiLink href={`#/projects/${doc._id}/strategies`}>
          {searchAggs[doc._id]?.strategies.toLocaleString() || 0}
        </EuiLink>
      ),
    },
    {
      field: 'benchmarks',
      name: 'Benchmarks',
      sortable: true,
      render: (name, doc) => (
        <EuiLink href={`#/projects/${doc._id}/benchmarks`}>
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
      name: 'Actions',
      actions: [
        {
          color: 'text',
          description: 'Manage displays',
          icon: 'palette',
          isPrimary: true,
          name: 'Displays',
          onClick: (doc) => {
            history.push({ pathname: `/projects/${doc._id}/displays` })
          },
          type: 'icon'
        },
        {
          color: 'text',
          description: 'Update this project',
          icon: 'documentEdit',
          isPrimary: true,
          name: 'Update',
          onClick: (doc) => setFlyout(doc),
          type: 'icon',
        },
        {
          color: 'danger',
          description: 'Delete this project',
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
      onCreated={(newDoc) => {
        // Redirect to displays
        history.push({ pathname: `/projects/${newDoc._id}/displays` })
      }}
      onSuccess={onSubmitSearch}
      setIsProcessing={setIsProcessing}
    />
  )

  const renderModalDelete = () => (
    <ModalDelete
      description={
        !!Object.keys((searchAggs[modalDelete._id]) || {}).length &&
        <EuiText>
          <p>This will delete all assets related to this project:</p>
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
      docType='project'
      isLoading={isProcessing}
      onClose={() => setModalDelete(null)}
      //onError={(e) => addToast(api.errorToast(e, { title: `Failed to delete project` }))}
      onDelete={async () => await api.projects_delete(modalDelete._id)}
      onSuccess={onSubmitSearch}
      setIsProcessing={setIsProcessing}
    />
  )

  const renderButtonCreate = () => (
    <EuiButton fill iconType='plusInCircle' onClick={() => setFlyout(true)}>
      Create a new project
    </EuiButton>
  )

  const renderModeIndicator = () => {
    if (mode === 'serverless') {
      return (
        <EuiBadge color="warning" iconType="cloud">
          Mode: Serverless
        </EuiBadge>
      )
    }
    return null
  }

  return (
    <Page
      title='Projects'
      buttons={[
        renderModeIndicator(),
        renderButtonCreate()
      ].filter(Boolean)}
    >
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

export default Projects