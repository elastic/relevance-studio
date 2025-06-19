import React, { useEffect, useMemo, useState } from 'react'
import {
  EuiButton,
  EuiCallOut,
  EuiInMemoryTable,
  EuiLink,
  EuiSkeletonText,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'
import { Page } from '../../Layout'
import FlyoutForm from './FlyoutForm'
import api from '../../api'

const Benchmarks = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const {
    project,
    isProjectReady,
    isProcessingBenchmark,
    loadAssets,
    benchmarks,
    benchmarksAggs,
    deleteBenchmark
  } = useProjectContext()

  /**
   * Load (or reload) any needed assets when project is ready.
   */
  useEffect(() => {
    if (isProjectReady)
      loadAssets({ benchmarks: true })
  }, [project?._id])

  /**
   * Benchmarks as an array for the table component
   */
  const benchmarksList = Object.values(benchmarks) || []

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

  ////  Render  ////////////////////////////////////////////////////////////////

  const columns = useMemo(() => {
    return [
      {
        field: '_id',
        name: 'Benchmark',
        sortable: true,
        truncateText: true,
        render: (name, doc) => (
          <EuiLink href={`#/projects/${project._id}/benchmarks/${doc._id}`}>
            {doc._id}
          </EuiLink>
        )
      },
      {
        field: '@timestamp',
        name: 'Time run',
        sortable: true,
        render: (name, doc) => new Date(doc['@timestamp']).toLocaleString()
      },
      {
        name: 'Actions',
        actions: [
          {
            color: 'text',
            description: 'Update this benchmark',
            icon: 'documentEdit',
            name: 'update',
            onClick: (doc) => setFlyout(doc),
            type: 'icon',
          },
          {
            color: 'danger',
            description: 'Delete this benchmark',
            icon: 'trash',
            name: 'delete',
            onClick: (doc) => setModalDelete(doc),
            type: 'icon',
          }
        ],
      }
    ]
  }, [benchmarks])

  /**
   * Button that navigates to the page to create a benchmark.
   */
  const buttonCreate = (
    <EuiButton
      fill
      iconType='plusInCircle'
      onClick={() => setFlyout(true)}>
      Create a new benchmark
    </EuiButton>
  )

  return (<>
    {modalDelete &&
      <ModalDelete
        description={
          !!benchmarksAggs[modalDelete._id]?.evaluations &&
          <EuiText>
            This will delete {benchmarksAggs[modalDelete._id]?.evaluations == 1 ? ' ' : 'all '}{benchmarksAggs[modalDelete._id]?.evaluations} evaluation{benchmarksAggs[modalDelete._id]?.evaluations == 1 ? '' : 's'} related to this benchmark.
          </EuiText>
        }
        doc={modalDelete}
        docType='benchmark'
        isLoading={isProcessingBenchmark}
        onClose={() => setModalDelete(null)}
        onError={(err) => addToast(api.errorToast(err, { title: `Failed to delete benchmark` }))}
        onDelete={async () => await deleteBenchmark(modalDelete)}
      />
    }
    {flyout &&
      <FlyoutForm
        action={flyout === true ? 'create' : 'update'}
        doc={flyout}
        onClose={() => setFlyout(null)}
        onCreated={(newDoc) => {
          // Add doc to table
          setProjects(prev => ({ ...prev, [newDoc._id]: newDoc }))
        }}
        onUpdated={(newDoc) => {
          // Update doc in table
          setProjects(prev => ({ ...prev, [newDoc._id]: newDoc }))
        }}
      />
    }
    <Page title='Benchmarks' buttons={[buttonCreate]}>
      <EuiSkeletonText isLoading={!isProjectReady} lines={10}>
        {!benchmarks &&
          <EuiCallOut
            color='primary'
            title='Welcome!'
          >
            <EuiText>
              Create your first benchmark to get started.
            </EuiText>
            <EuiSpacer size='m' />
            {buttonCreate}
          </EuiCallOut>
        }
        {!!benchmarks &&
          <EuiInMemoryTable
            columns={columns}
            items={benchmarksList}
            pagination={true}
            responsiveBreakpoint={false}
            sorting={{
              sort: {
                field: '@timestamp',
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

export default Benchmarks