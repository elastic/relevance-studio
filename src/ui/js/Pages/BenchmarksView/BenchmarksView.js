import { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiCode,
  EuiLink,
  EuiSkeletonTitle,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { usePageResources, useResources } from '../../Contexts/ResourceContext'
import { useSearchHandler } from '../../Hooks'
import { ModalDelete, Page, SearchTable } from '../../Layout'
import api from '../../api'
import utils from '../../utils'

const BenchmarksView = () => {

  ////  Context  ///////////////////////////////////////////////////////////////
  
  const { addToast, autoRefresh } = useAppContext()
  const { workspace, benchmark } = usePageResources()
  const isReady = useResources().hasResources(['workspace', 'benchmark'])

  ////  State  /////////////////////////////////////////////////////////////////

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
  const [searchSortField, setSearchSortField] = useState("@meta.created_at") // TODO: Implement @meta.last_updated
  const [searchSortOrder, setSearchSortOrder] = useState("desc")
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
  }, [isReady, searchPage])

  /**
   * Search handler
   */
  const onSubmitSearch = useSearchHandler({
    searchFn: api.evaluations_search, // search evaluations
    workspaceId: workspace?._id,
    resourceId: benchmark?._id,
    searchText,
    searchPage,
    searchSize,
    searchSortField,
    searchSortOrder,
    useAggs: false, // evaluations don't have aggs
    setDocs: (docs) => {
      /**
       * Evaluations as an array for the table component.
       * Add additional fields for the table.
       */
      const evaluationsList = Object.values(docs) || []
      const dateFields = ['created_at', 'started_at', 'stopped_at']
      for (const e in evaluationsList) {
        const lastUpdated = new Date(Math.max(
          ...dateFields
            .map(k => new Date(evaluationsList[e]["@meta"]?.[k] || 0).getTime())
        )).toISOString()
        evaluationsList[e]['@meta']['last_updated'] = lastUpdated
      }
      setSearchDocs(evaluationsList)
    },
    setTotal: setSearchTotal,
    setLoading: setIsSearchLoading,
    setHasEverSearched: setHasEverSearched,
    setIsIndexEmpty: setIsIndexEmpty,
  })

  /**
   * Enable or disable auto-refresh.
   */
  useEffect(() => {
    if (!isReady || !autoRefresh)
      return
    const interval = setInterval(() => {
      onSubmitSearch()
      setSearchPage(1) // TODO: Try to remove this so we don't always return to page 1 on auto-refresh
    }, 5000)
    return () => clearInterval(interval)
  }, [isReady, autoRefresh])

  const onRunEvaluationSubmit = async (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();
    let response
    try {
      setIsProcessing(true)
      response = await api.evaluations_create(
        workspace._id,
        benchmark._id,
        benchmark.task
      )
    } catch (e) {
      return addToast(api.errorToast(e, { title: 'Failed to queue evaluation' }))
    } finally {
      setIsProcessing(false)
    }

    // Handle API response
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    addToast(utils.toastDocCreateUpdateDelete('queue', 'evaluation', response.data._id))

    // Reload table
    onSubmitSearch()
    setSearchPage(1)
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const columns = [
    {
      field: '_id',
      name: 'Evaluation',
      sortable: true,
      style: { width: '300px' },
      render: (name, doc) => (
        <EuiLink href={`#/workspaces/${workspace._id}/benchmarks/${benchmark._id}/evaluations/${doc._id}`}>
          <EuiCode transparentBackground style={{ color: 'inherit', fontSize: '12px', fontWeight: 'normal', padding: 0 }}>
            {doc._id}
          </EuiCode>
        </EuiLink>
      )
    },
    {
      field: '@meta.status',
      name: 'Status',
      sortable: true,
      style: { width: '120px' },
      render: (name, doc) => {
        if (doc['@meta']?.status == 'completed')
          return (
            <EuiBadge color='success'>
              Completed
            </EuiBadge>
          )
        if (doc['@meta']?.status == 'failed')
          return (
            <EuiBadge color='danger'>
              Failed
            </EuiBadge>
          )
        if (doc['@meta']?.status == 'skipped')
          return (
            <EuiBadge color='text'>
              Skipped
            </EuiBadge>
          )
        if (doc['@meta']?.status == 'running')
          // Evaluations are "stale" if they are running for more than 2 hours
          if (Date.now() - new Date(doc['@meta']?.started_at).getTime() > 2 * 60 * 60 * 1000) {
            return (
              <EuiBadge color='accent'>
                Stale
              </EuiBadge>
            )
          } else {
            return (
              <EuiBadge color='primary'>
                Running
              </EuiBadge>
            )
          }
        if (doc['@meta']?.status == 'pending')
          return (
            <EuiBadge color='text'>
              Pending
            </EuiBadge>
          )
        return (
          <EuiBadge color='hollow'>
            Unknown
          </EuiBadge>
        )
      }
    },
    {
      field: '@meta.last_updated',
      name: 'Updated',
      sortable: true,
      style: { width: '150px' },
      render: (name, doc) => doc['@meta']?.last_updated ? utils.timeAgo(doc['@meta']?.last_updated) : '-'
    },
    {
      field: 'took',
      name: 'Duration',
      sortable: true,
      style: { width: '100px' },
      render: (name, doc) => doc.took ? utils.formatDuration(doc.took) : '-'
    },
    {
      field: 'num_strategies',
      name: 'Strategies',
      sortable: true,
      render: (name, doc) => doc.strategy_id?.length || '-'
    },
    {
      field: 'num_scenarios',
      name: 'Scenarios',
      sortable: true,
      render: (name, doc) => doc.scenario_id?.length || '-'
    },
    {
      name: 'Actions',
      actions: [
        {
          color: 'danger',
          description: 'Delete this evaluation',
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
      doc={modalDelete}
      docType='evaluation'
      isProcessing={isProcessing}
      onClose={() => setModalDelete(null)}
      onDelete={async () => await api.evaluations_delete(workspace._id, benchmark._id, modalDelete._id)}
      onSuccess={onSubmitSearch}
      setIsProcessing={setIsProcessing}
    />
  )

  const renderButtonRun = () => (
    <EuiButton
      fill
      iconType='play'
      isLoading={isProcessing}
      onClick={onRunEvaluationSubmit}>
      Run evaluation
    </EuiButton>
  )

  return (
    <Page title={
      <EuiSkeletonTitle isLoading={!isReady} size='l'>
        {!benchmark?.name &&
          <>Not found</>
        }
        {!!benchmark?.name &&
          <>{benchmark.name}</>
        }
      </EuiSkeletonTitle>
    }
      buttons={[renderButtonRun()]}
    >
      {modalDelete && renderModalDelete()}
      {hasEverSearched &&
        <>
          {isIndexEmpty &&
            <EuiCallOut
              color='primary'
              title='Welcome!'
            >
              <EuiText>
                Run your first evaluation for this benchmark.
              </EuiText>
              <EuiSpacer size='m' />
              {renderButtonRun()}
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
              showAutoRefresh={true}
            />
          }
        </>
      }
    </Page>
  )
}

export default BenchmarksView