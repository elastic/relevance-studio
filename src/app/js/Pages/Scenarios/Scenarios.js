import React, { useEffect, useMemo, useState } from 'react'
import { useHistory } from 'react-router-dom'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiCodeBlock,
  EuiInMemoryTable,
  EuiLink,
  EuiSkeletonText,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'
import { ModalDelete, Page } from '../../Layout'
import FlyoutForm from './FlyoutForm'
import api from '../../api'

const Scenarios = () => {

  const history = useHistory()

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const {
    project,
    isProjectReady,
    isLoadingScenario,
    loadAssets,
    scenarios,
    scenariosAggs,
    deleteScenario
  } = useProjectContext()

  /**
   * Load (or reload) any needed assets when project is ready.
   */
  useEffect(() => {
    if (isProjectReady)
      loadAssets({ scenarios: true })
  }, [project?._id])

  /**
   * Scenarios as an array for the table component
   */
  const scenariosList = Object.values(scenarios) || []

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
                isCopyable
                language='json'
                overflowHeight={140}
                paddingSize='s'
                style={{ fontSize: '11px' }}
              >
                {JSON.stringify(doc.values, null, 2)}
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
        sortable: (doc) => {
          const count = scenariosAggs?.[doc._id]?.judgements ?? 0
          return count
        },
        render: (name, doc) => {
          const count = scenariosAggs?.[doc._id]?.judgements ?? 0
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
      /*{
        field: 'evaluations',
        name: 'Evaluations',
        width: '100px',
        render: (name, doc) => {
          const count = scenariosAggs?.[doc._id]?.evaluations ?? 0
          return (
            <EuiLink href={`#/projects/${project._id}/evaluations`}>
              {count.toLocaleString()}
            </EuiLink>
          )
        }
      },*/
      {
        name: 'Actions',
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
  }, [scenarios])

  const buttonCreate = (
    <EuiButton
      fill
      iconType='plusInCircle'
      onClick={() => setFlyout(true)}>
      Create a new scenario
    </EuiButton>
  )

  return (<>
    {modalDelete &&
      <ModalDelete
        description={
          !!scenariosAggs[modalDelete._id]?.judgements &&
          <EuiText>
            This will delete {scenariosAggs[modalDelete._id]?.judgements == 1 ? ' ' : 'all '}{scenariosAggs[modalDelete._id]?.judgements} judgement{scenariosAggs[modalDelete._id]?.judgements == 1 ? '' : 's'} related to this scenario.
          </EuiText>
        }
        doc={modalDelete}
        docType='scenario'
        isLoading={isLoadingScenario}
        onClose={() => setModalDelete(null)}
        onError={(err) => addToast(api.errorToast(err, { title: `Failed to delete scenario` }))}
        onDelete={async () => await deleteScenario(modalDelete)}
      />
    }
    {flyout &&
      <FlyoutForm
        action={flyout === true ? 'create' : 'update'}
        doc={flyout}
        onClose={() => setFlyout(null)}
      />
    }
    <Page title='Scenarios' buttons={[buttonCreate]}>
      <EuiSkeletonText isLoading={!isProjectReady} lines={10}>
        {!scenarios &&
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
        {!!scenarios &&
          <EuiInMemoryTable
            columns={columns}
            items={scenariosList}
            pagination={true}
            responsiveBreakpoint={false}
            sorting={{
              sort: {
                field: 'name',
                direction: 'asc',
              }
            }}
            tableLayout='custom'
          />
        }
      </EuiSkeletonText>
    </Page>
  </>)
}

export default Scenarios