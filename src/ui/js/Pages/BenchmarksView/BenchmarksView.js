import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
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
import { useProjectContext } from '../../Contexts/ProjectContext'
import { useSearchHandler } from '../../Hooks'
import { ModalDelete, Page, SearchTable } from '../../Layout'
import api from '../../api'
import utils from '../../utils'

const BenchmarksView = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, autoRefresh } = useAppContext()
  const { project, isProjectReady } = useProjectContext()

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
  const [benchmark, setBenchmark] = useState({})
  const [benchmarkId, setBenchmarkId] = useState(null)
  const [isLoadingBenchmark, setIsLoadingBenchmark] = useState(false)
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
   * Parse benchmarkId from URL path
   */
  const { benchmark_id } = useParams()
  useEffect(() => setBenchmarkId(benchmark_id), [benchmark_id])

  /**
   * Get benchmark on page load
   */
  useEffect(() => {
    if (!project?._id || !benchmarkId)
      return
    (async () => {
      // Submit API request
      let response
      try {
        setIsLoadingBenchmark(true)
        response = await api.benchmarks_get(project._id, benchmarkId)
      } catch (e) {
        return addToast(api.errorToast(e, { title: 'Failed to get benchmark' }))
      } finally {
        setIsLoadingBenchmark(false)
      }
      // Handle API response
      setBenchmark(response.data._source)
    })()
  }, [project, benchmarkId])

  /**
   * Automatically submit the search and return to page one either when the
   * project is ready or when the user changes pagination settings.
   */
  useEffect(() => {
    if (isProjectReady && benchmarkId) {
      onSubmitSearch()
      setSearchPage(1)
    }
  }, [project?._id, benchmarkId, searchSize, searchSortField, searchSortOrder])

  /**
   * Automatically submit the search when the user selects a different page in
   * the search results.
   */
  useEffect(() => {
    if (isProjectReady && benchmarkId)
      onSubmitSearch()
  }, [searchPage, project?._id, benchmarkId])

  /**
   * Search handler
   */
  const onSubmitSearch = useSearchHandler({
    searchFn: api.evaluations_search, // search evaluations
    projectId: project?._id,
    resourceId: benchmarkId,
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
    if (!isProjectReady || !benchmarkId || !autoRefresh)
      return
    const interval = setInterval(() => {
      onSubmitSearch()
      setSearchPage(1) // TODO: Try to remove this so we don't always return to page 1 on auto-refresh
    }, 5000)
    return () => clearInterval(interval)
  }, [project?._id, benchmarkId, autoRefresh])

  const onRunEvaluationSubmit = async (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();
    let response
    try {
      setIsProcessing(true)
      response = await api.evaluations_create(
        project._id,
        benchmarkId,
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
        <EuiLink href={`#/projects/${project._id}/benchmarks/${benchmarkId}/evaluations/${doc._id}`}>
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
      onDelete={async () => await api.evaluations_delete(project._id, benchmarkId, modalDelete._id)}
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
      <EuiSkeletonTitle isLoading={isLoadingBenchmark} size='l'>
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