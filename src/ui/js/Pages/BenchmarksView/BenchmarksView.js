import React, { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiCode,
  EuiInMemoryTable,
  EuiLink,
  EuiSkeletonText,
  EuiSkeletonTitle,
  EuiSpacer,
  EuiSwitch,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'
import { ModalDelete, Page } from '../../Layout'
import api from '../../api'
import utils from '../../utils'

const BenchmarksView = () => {

  /**
   * benchmarkId comes from the URL path: /projects/:project_id/benchmarks/:benchmark_id
   */
  const { benchmark_id: benchmarkId } = useParams()

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, autoRefresh, setAutoRefresh } = useAppContext()
  const {
    project,
    isProjectReady,
    loadAssets,
    isLoadingBenchmarks,
    benchmarks,
    evaluations,
  } = useProjectContext()

  /**
   * Load (or reload) any needed assets when project is ready.
   * Enable or disable auto-refresh.
   */
  useEffect(() => {
    if (isProjectReady && benchmarkId)
      loadAssets({ benchmarks: benchmarkId, evaluations: benchmarkId })
  }, [project?._id, benchmarkId])

  /**
   * Enable or disable auto-refresh.
   */
  useEffect(() => {
    if (!isProjectReady || !benchmarkId || !autoRefresh)
      return
    const interval = setInterval(() => {
      loadAssets({ evaluations: benchmarkId })
    }, 5000)
    return () => clearInterval(interval)
  }, [project?._id, benchmarkId, autoRefresh])

  /**
   * Evaluations as an array for the table component.
   * Add additional fields for the table.
   */
  const evaluationsList = Object.values(evaluations) || []
  const dateFields = ['created_at', 'started_at', 'stopped_at']
  for (const e in evaluationsList) {
    const lastUpdated = new Date(Math.max(
      ...dateFields
        .map(k => new Date(evaluationsList[e]["@meta"]?.[k] || 0).getTime())
    )).toISOString()
    evaluationsList[e]['@meta']['last_updated'] = lastUpdated
  }

  ////  State  /////////////////////////////////////////////////////////////////

  const [isProcessingEvaluation, setIsProcessingEvaluation] = useState(false)

  /**
   * null:   close modal
   * object: open modal to delete a given doc (object)
   */
  const [modalDelete, setModalDelete] = useState(null)

  const onRunEvaluationSubmit = (e) => {
    e.preventDefault();
    (async () => {
      try {
        let response
        try {
          setIsProcessingEvaluation(true)
          response = await api.evaluations_create(
            project._id,
            benchmarkId,
            benchmarks[benchmarkId].task
          )
        } catch (error) {
          return addToast(api.errorToast(error, {
            title: 'Failed to run evaluation'
          }))
        } finally {
          setIsProcessingEvaluation(false)
        }

        // Handle API response
        if (response.status < 200 && response.status > 299)
          return addToast(utils.toastClientResponse(response))

        addToast({
          title: 'Queued valuation',
          color: 'success',
          iconType: 'check',
          text: (
            <EuiText size='xs'>
              <EuiText color='subdued' size='xs'>
                <small>{response.data._id}</small>
              </EuiText>
            </EuiText>
          )
        })

        // Reload table
        loadAssets({ evaluations: benchmarkId })

      } finally {
        setIsProcessingEvaluation(false)
      }
    })()
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const columns = useMemo(() => {
    return [
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
  }, [evaluations])

  /**
   * Button that toggles automatically refreshing tables.
   */
  const buttonAutoRefresh = (
    <EuiSwitch
      checked={autoRefresh}
      compressed
      label='Auto-refresh'
      onClick={() => setAutoRefresh(!autoRefresh)}
      style={{ align: 'right' }}
    />
  )

  /**
   * Button that queues an evaluation to be run.
   */
  const buttonRun = (
    <EuiButton
      fill
      iconType='play'
      isLoading={isProcessingEvaluation}
      onClick={onRunEvaluationSubmit}>
      Run evaluation
    </EuiButton>
  )

  return (
    <Page title={
      <EuiSkeletonTitle isLoading={isLoadingBenchmarks} size='l'>
        {!benchmarks?.[benchmarkId] &&
          <>Not found</>
        }
        {!!benchmarks?.[benchmarkId] &&
          <>{benchmarks[benchmarkId].name}</>
        }
      </EuiSkeletonTitle>
    }
      buttons={[buttonRun]}
    >
      {modalDelete &&
        <ModalDelete
          doc={modalDelete}
          docType='evaluation'
          isLoading={isProcessingEvaluation}
          onClose={() => setModalDelete(null)}
          onError={(err) => addToast(api.errorToast(err, { title: `Failed to delete evaluation` }))}
          onDelete={async () => {
            console.debug(`Deleting evaluation for project: ${project._id}`)
            let response
            try {
              setIsProcessingEvaluation(true)
              response = await api.evaluations_delete(project._id, benchmarkId, modalDelete._id)
            } catch (err) {
              return addToast(api.errorToast(err, { title: `Failed to delete evaluation` }))
            } finally {
              setIsProcessingEvaluation(false)
            }
            // Handle API response
            if (response.status > 299)
              return addToast(utils.toastClientResponse(response))
            addToast(utils.toastDocCreateUpdateDelete('delete', 'evaluation', modalDelete._id, modalDelete))

            // Reload table
            loadAssets({ evaluations: benchmarkId })
          }}
        />
      }
      <EuiSkeletonText isLoading={!evaluations} lines={10}>
        {!evaluations &&
          <EuiCallOut
            color='primary'
            title='Welcome!'
          >
            <EuiText>
              Create your first evaluation to get started.
            </EuiText>
            <EuiSpacer size='m' />
            {buttonCreate}
          </EuiCallOut>
        }
        {!!evaluations &&
          <>
            <div style={{ textAlign: 'right' }}>
              {buttonAutoRefresh}
            </div>
            <EuiSpacer size='l' />
            <EuiInMemoryTable
              columns={columns}
              items={evaluationsList}
              pagination={true}
              responsiveBreakpoint={false}
              sorting={{
                sort: {
                  field: '@meta.last_updated',
                  direction: 'desc',
                }
              }}
              tableLayout='auto'
            />
          </>
        }
      </EuiSkeletonText>
    </Page>
  )
}

export default BenchmarksView