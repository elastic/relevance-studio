/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useRef, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiButtonEmpty,
  EuiCallOut,
  EuiCode,
  EuiConfirmModal,
  EuiLink,
  EuiLoadingSpinner,
  EuiProgress,
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
   * null:   close the run confirmation modal
   * object: open it with `estimate` (the cost of the run) and `duration`
   *         (`loading`, `unavailable` or `{ low_ms, high_ms }`)
   */
  const [runConfirm, setRunConfirm] = useState(null)

  /**
   * Identifies the latest duration estimate, so a late response for a closed or
   * replaced modal gets ignored.
   */
  const durationRequest = useRef(0)

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
    searchFn: api.runs_search, // search runs
    workspaceId: workspace?._id,
    resourceId: benchmark?._id,
    searchText,
    searchPage,
    searchSize,
    searchSortField,
    searchSortOrder,
    useAggs: false, // runs don't have aggs
    setDocs: (docs) => {
      /**
       * Runs as an array for the table component.
       * Add additional fields for the table.
       */
      const runsList = Object.values(docs) || []
      const dateFields = ['created_at', 'started_at', 'stopped_at']
      for (const e in runsList) {
        const lastUpdated = new Date(Math.max(
          ...dateFields
            .map(k => new Date(runsList[e]["@meta"]?.[k] || 0).getTime())
        )).toISOString()
        runsList[e]['@meta']['last_updated'] = lastUpdated
      }
      setSearchDocs(runsList)
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

  /**
   * Check the cost of a run and ask for confirmation before queueing it. The
   * modal opens with the counts right away. Then a short latency probe against
   * the content cluster measures the search speed to estimate the duration.
   */
  const onRunBenchmarkSubmit = async (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();
    let response
    try {
      setIsProcessing(true)
      response = await api.benchmarks_estimate(workspace._id, { task: benchmark.task })
    } catch (e) {
      return addToast(api.errorToast(e, { title: 'Failed to estimate the run' }))
    } finally {
      setIsProcessing(false)
    }
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    const estimate = response.data
    if (estimate.errors?.length) {
      return addToast({
        color: 'danger',
        title: `This run can't start`,
        text: estimate.errors.join(' '),
      })
    }
    const request = ++durationRequest.current
    setRunConfirm({ estimate, duration: 'loading' })
    estimateDuration(request)
  }

  /**
   * Estimate the duration of the run for the open modal. Ignore the response if
   * the user closed the modal or opened another one in the meantime.
   */
  const estimateDuration = async (request) => {
    let duration = 'unavailable'
    let estimate = null
    try {
      const response = await api.benchmarks_estimate(workspace._id, { task: benchmark.task, probe: true })
      if (response.status <= 299 && response.data) {
        estimate = response.data
        if (estimate.duration)
          duration = { low_ms: estimate.duration.low_ms, high_ms: estimate.duration.high_ms }
      }
    } catch (e) {
      // Leave the duration unavailable. The user can still run the benchmark.
    }
    if (request !== durationRequest.current)
      return
    setRunConfirm(prev => prev && ({ estimate: estimate || prev.estimate, duration }))
  }

  const onRecalculateDuration = () => {
    const request = ++durationRequest.current
    setRunConfirm(prev => prev && ({ ...prev, duration: 'loading' }))
    estimateDuration(request)
  }

  const closeRunConfirm = () => {
    durationRequest.current++
    setRunConfirm(null)
  }

  const queueRun = async () => {
    let response
    try {
      setIsProcessing(true)
      response = await api.runs_create(
        workspace._id,
        benchmark._id,
        benchmark.task
      )
    } catch (e) {
      return addToast(api.errorToast(e, { title: 'Failed to queue run' }))
    } finally {
      setIsProcessing(false)
    }

    // Handle API response
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    addToast(utils.toastDocCreateUpdateDelete('queue', 'run', response.data._id))

    // Reload table
    onSubmitSearch()
    setSearchPage(1)
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const columns = [
    {
      field: '_id',
      name: 'Run',
      sortable: true,
      style: { width: '300px' },
      render: (name, doc) => (
        <EuiLink href={`#/workspaces/${workspace._id}/benchmarks/${benchmark._id}/runs/${doc._id}`}>
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
          // Runs are "stale" if they are running for more than 2 hours
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
      field: 'progress',
      name: 'Progress',
      sortable: false,
      style: { width: '100px' },
      // Styled to match the metric/"Rated docs" progress bars in the run
      // view's summary table (TableMetrics.js): a single `size='s'`,
      // `color='vis0'` bar, normalized to max={1}.
      render: (progress) => {
        const total = progress?.requests_total
        // No progress to show for runs that haven't started (pending) or that
        // had nothing to run (skipped: no scenarios with judgements).
        if (!Number.isInteger(total) || total <= 0)
          return <EuiText size='s'>-</EuiText>
        const completed = Number.isInteger(progress?.requests_completed) ? progress.requests_completed : 0
        return (
          <div style={{ position: 'relative', width: '100%' }}>
            <EuiProgress
              color='vis0'
              max={1}
              size='m'
              value={completed / total}
            />
          </div>
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
      field: 'task.requests',
      name: 'Searches',
      sortable: true,
      render: (name, doc) => Number.isInteger(doc.task?.requests) ? doc.task.requests.toLocaleString() : '-'
    },
    {
      name: 'Actions',
      actions: [
        {
          color: 'danger',
          description: 'Delete this run',
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
      docType='run'
      isProcessing={isProcessing}
      onClose={() => setModalDelete(null)}
      onDelete={async () => await api.runs_delete(workspace._id, benchmark._id, modalDelete._id)}
      onSuccess={onSubmitSearch}
      setIsProcessing={setIsProcessing}
    />
  )

  const METRIC_LABELS = { mrr: 'MRR', ndcg: 'NDCG', precision: 'Precision', recall: 'Recall' }

  const renderRunDuration = () => {
    const { duration } = runConfirm
    if (duration === 'loading') {
      return (
        <>
          <EuiLoadingSpinner size='s' /> Calculating...
        </>
      )
    }
    let text = <span>Unavailable</span>
    if (duration !== 'unavailable') {
      text = <b>~{utils.formatDuration((duration.low_ms + duration.high_ms) / 2)}</b>
    }
    return (
      <>
        {text}
        {' '}
        <EuiButtonEmpty
          color='text'
          iconType='refresh'
          onClick={onRecalculateDuration}
          size='xs'
          style={{ blockSize: 'auto' }}
        >
          Recalculate
        </EuiButtonEmpty>
      </>
    )
  }

  const renderModalRunConfirm = () => {
    const { estimate } = runConfirm
    const strategies = estimate.strategies?.length || 0
    const metrics = benchmark.task?.metrics || []
    return (
      <EuiConfirmModal
        cancelButtonText='Cancel'
        confirmButtonText='Run benchmark'
        onCancel={closeRunConfirm}
        onConfirm={async () => {
          closeRunConfirm()
          await queueRun()
        }}
        title='Run this benchmark?'
      >
        <EuiText size='s'>
          <p>This will run <b>{estimate.searches.total.toLocaleString()}</b> searches that cover:</p>
          <ul>
            <li><b>{strategies.toLocaleString()}</b> {strategies === 1 ? 'strategy' : 'strategies'}</li>
            <li><b>{estimate.variants.toLocaleString()}</b> {estimate.variants === 1 ? 'variant' : 'variants'}</li>
            <li>
              <b>{metrics.length.toLocaleString()}</b> relevance {metrics.length === 1 ? 'metric' : 'metrics'}
              {metrics.length > 0 && <> ({metrics.map((metric) => METRIC_LABELS[metric] || metric).join(', ')})</>}
            </li>
          </ul>
          <p>Estimated duration: {renderRunDuration()}</p>
        </EuiText>
        {estimate.warnings?.map((message) => (
          <div key={message}>
            <EuiSpacer size='s' />
            <EuiCallOut color='warning' iconType='warning' size='s'>
              <p>{message}</p>
            </EuiCallOut>
          </div>
        ))}
      </EuiConfirmModal>
    )
  }

  const renderButtonRun = () => (
    <EuiButton
      fill
      iconType='play'
      isLoading={isProcessing}
      onClick={onRunBenchmarkSubmit}>
      Run benchmark
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
      {runConfirm && renderModalRunConfirm()}
      {hasEverSearched &&
        <>
          {isIndexEmpty &&
            <EuiCallOut
              color='primary'
              title='Welcome!'
            >
              <EuiText>
                Run this benchmark for the first time.
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