import React, { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiInMemoryTable,
  EuiLink,
  EuiSkeletonText,
  EuiSkeletonTitle,
  EuiSpacer,
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

  const { addToast } = useAppContext()
  const {
    project,
    isProjectReady,
    loadAssets,
    benchmarks,
    evaluations,
    createEvaluation,
    deleteEvaluation
  } = useProjectContext()

  /**
   * Load (or reload) any needed assets when project is ready.
   */
  useEffect(() => {
    if (isProjectReady)
      loadAssets({ benchmarks: benchmarkId, evaluations: benchmarkId })
  }, [project?._id])

  /**
   * Evaluations as an array for the table component.
   * Add additional fields for the table.
   */
  const evaluationsList = Object.values(evaluations) || []
  const dateFields = [ 'created_at', 'started_at', 'stopped_at' ]
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
        setIsProcessingEvaluation(true)
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
          title: 'Queued evaluation',
          color: 'success',
          iconType: 'check'
        })

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
        name: 'Evaluation ID',
        sortable: true,
        truncateText: true,
        render: (name, doc) => (
          <EuiLink href={`#/projects/${project._id}/benchmarks/${benchmarkId}/evaluations/${doc._id}`}>
            {doc._id}
          </EuiLink>
        )
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
        field: '@meta.status',
        name: 'Status',
        sortable: true,
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
            return (
              <EuiBadge color='primary'>
                Running
              </EuiBadge>
            )
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
        render: (name, doc) => doc['@meta']?.last_updated ? utils.timeAgo(doc['@meta']?.last_updated) : '-'
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

  return (<>
    {modalDelete &&
      <ModalDelete
        doc={modalDelete}
        docType='evaluation'
        isLoading={isProcessingEvaluation}
        onClose={() => setModalDelete(null)}
        onError={(err) => addToast(api.errorToast(err, { title: `Failed to delete evaluation` }))}
        onDelete={async () => await deleteEvaluation(modalDelete._id)}
      />
    }
    <Page title={
      <EuiSkeletonTitle isLoading={!isProjectReady} size='l'>
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
      <EuiSkeletonText isLoading={!isProjectReady} lines={10}>
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
        }
      </EuiSkeletonText>
    </Page>
  </>)
}

export default BenchmarksView