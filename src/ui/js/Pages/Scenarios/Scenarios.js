import { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiCodeBlock,
  EuiLink,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import { useProjectContext } from '../../Contexts/ProjectContext'
import { useSearchHandler } from '../../Hooks'
import { ModalDelete, Page, SearchTable } from '../../Layout'
import FlyoutForm from './FlyoutForm'
import api from '../../api'
import { getHistory } from '../../history'

const Scenarios = () => {

  const history = getHistory()

  ////  Context  ///////////////////////////////////////////////////////////////

  const { project, isProjectReady } = useProjectContext()

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
   * project is ready or when the user changes pagination settings.
   */
  useEffect(() => {
    if (isProjectReady) {
      onSubmitSearch()
      setSearchPage(1)
    }
  }, [project?._id, searchSize, searchSortField, searchSortOrder])

  /**
   * Automatically submit the search when the user selects a different page in
   * the search results.
   */
  useEffect(() => {
    if (isProjectReady)
      onSubmitSearch()
  }, [searchPage])

  /**
   * Search handler
   */
  const onSubmitSearch = useSearchHandler({
    searchFn: api.scenarios_search, // search scenarios
    projectId: project?._id,
    searchText,
    searchPage,
    searchSize,
    searchSortField,
    searchSortOrder,
    useAggs: true, // scenarios have aggs
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
      name: 'Scenario',
      sortable: true,
      truncateText: true,
      width: '100px',
      render: (name, doc) => <>{doc.name}</>
    },
    {
      field: 'values',
      name: 'Values',
      render: (name, doc) => {
        return (
          <div style={{ width: '100%' }}>
            <EuiCodeBlock
              language='json'
              paddingSize='s'
              style={{ fontSize: '11px' }}
              transparentBackground
            >
              {JSON.stringify(doc.values)}
            </EuiCodeBlock>
          </div>
        )
      },
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
      field: 'judgements',
      name: 'Judgements',
      width: '100px',
      render: (name, doc) => {
        const count = searchAggs?.[doc._id]?.judgements ?? 0
        return (
          <EuiLink onClick={(e) => {
            history.push({
              pathname: `/projects/${project._id}/judgements`,
              state: {
                query_on_load: {
                  scenario: doc,
                  filter: 'rated'
                }
              }
            })
          }}>
            {count.toLocaleString()}
          </EuiLink>
        )
      }
    },
    {
      name: 'Actions',
      width: '100px',
      actions: [
        {
          color: 'text',
          description: 'Update this scenario',
          icon: 'documentEdit',
          name: 'update',
          onClick: (doc) => setFlyout(doc),
          type: 'icon',
        },
        {
          color: 'danger',
          description: 'Delete this scenario',
          icon: 'trash',
          name: 'delete',
          onClick: (doc) => setModalDelete(doc),
          type: 'icon',
        }
      ],
    }
  ]

  const renderModalDelete = () => (
    <ModalDelete
      description={
        !!searchAggs[modalDelete._id]?.judgements &&
        <EuiText>
          This will delete {searchAggs[modalDelete._id]?.judgements == 1 ? ' ' : 'all '}{searchAggs[modalDelete._id]?.judgements} judgement{searchAggs[modalDelete._id]?.judgements == 1 ? '' : 's'} related to this scenario.
        </EuiText>
      }
      doc={modalDelete}
      docType='scenario'
      isProcessing={isProcessing}
      onClose={() => setModalDelete(null)}
      onDelete={async () => await api.scenarios_delete(project._id, modalDelete._id)}
      onSuccess={onSubmitSearch}
      setIsProcessing={setIsProcessing}
    />
  )

  const renderFlyout = () => (
    <FlyoutForm
      action={flyout === true ? 'create' : 'update'}
      doc={flyout}
      isProcessing={isProcessing}
      onClose={() => setFlyout(null)}
      onSuccess={onSubmitSearch}
      setIsProcessing={setIsProcessing}
    />
  )

  const renderButtonCreate = () => (
    <EuiButton fill iconType='plusInCircle' onClick={() => setFlyout(true)}>
      Create a new scenario
    </EuiButton>
  )

  return (
    <Page title='Scenarios' buttons={[renderButtonCreate()]}>
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

export default Scenarios