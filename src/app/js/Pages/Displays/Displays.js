import React, { useEffect, useMemo, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiFieldText,
  EuiForm,
  EuiFormRow,
  EuiIcon,
  EuiInMemoryTable,
  EuiLink,
  EuiModal,
  EuiModalHeaderTitle,
  EuiModalBody,
  EuiModalFooter,
  EuiModalHeader,
  EuiSkeletonText,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'
import { ModalDelete, Page } from '../../Layout'
import api from '../../api'

const Displays = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const {
    project,
    isProjectReady,
    isProcessingDisplay,
    loadAssets,
    displays,
    createDisplay,
    updateDisplay,
    deleteDisplay
  } = useProjectContext()

  /**
   * Load (or reload) any needed assets when project is ready.
   */
  useEffect(() => {
    if (isProjectReady)
      loadAssets({ indices: true, displays: true })
  }, [project?._id])

  /**
   * Displays as an array for the table component
   */
  const displaysList = Object.values(displays) || []

  ////  State  /////////////////////////////////////////////////////////////////

  /**
   * null:   close modal
   * true:   open modal to create a new doc
   */
  const [modalCreate, setModalCreate] = useState(null)

  /**
   * null:   close modal
   * object: open modal to update a given doc (object)
   */
  const [modalUpdate, setModalUpdate] = useState(null)
  /**
   * null:   close modal
   * object: open modal to delete a given doc (object)
   */
  const [modalDelete, setModalDelete] = useState(null)

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onSubmit = async (e) => {
    e.preventDefault();
    if (modalCreate) {

      // Create display and redirect to its editor
      const doc = { ...modalCreate }
      doc.index_pattern = doc.index_pattern.trim()
      const response = await createDisplay(doc)
      window.location.href = `/#/projects/${project._id}/displays/${response.data._id}`
      return setModalCreate(null)
    } else {

      // Update display and close modal
      const doc = { ...modalUpdate }
      doc.index_pattern = doc.index_pattern.trim()
      await updateDisplay(doc)
      return setModalUpdate(null)
    }
  }

  /**
   * Check if the index pattern of the display is within the scope of the
   * index pattern of the project. Both can have commas, so those are split,
   * and if any of the input splits matches any of the target splits,
   * then consider the whole thing to be a match.
   */
  const isIndexPatternInProjectScope = (inputPattern, targetPattern) => {
    const toParts = (pattern) => pattern.split(',').map(p => p.trim()).filter(Boolean)
    const toRegex = (glob) => new RegExp('^' + glob.replace(/[-[\]/{}()+?.\\^$|]/g, '\\$&').replace(/\*/g, '.*') + '$')
    const inputs = toParts(inputPattern)
    const targets = toParts(targetPattern)
    return inputs.some(input =>
      targets.some(target =>
        toRegex(target).test(input) || toRegex(input).test(target)
      )
    )
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const indexPatternInput = (modalCreate?.index_pattern || modalUpdate?.index_pattern) || ''
  const indexPatternInScope = project ? isIndexPatternInProjectScope(indexPatternInput, project.index_pattern) : false

  /**
   * Modal to create or update a display.
   */
  const renderModalCreateUpdate = () => (
    <EuiModal onClose={() => { setModalCreate(null); setModalUpdate(null) }}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          {modalCreate ? 'Create a new display' : 'Update display'}
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiForm component='form' id='create-update'>
          <EuiFormRow label='Index Pattern' helpText={<>
            <p>
              An <a href='https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-multiple-data-streams-indices' target='_blank'>index pattern</a> whose documents will render with this display.<br/>It must be a subset of this project's index pattern.
            </p>
            <br />
            <p>
              Project index pattern: <b>{project?.index_pattern}</b>
            </p>
            <br />
            {indexPatternInput.trim() == '' &&
              <p><small>&nbsp;</small></p>
            }
            {indexPatternInput.trim() != '' &&
              <p>
                <EuiIcon
                  color={indexPatternInScope ? 'success' : 'danger'}
                  size='s'
                  style={{ marginRight: '10px' }}
                  type={indexPatternInScope ? 'check' : 'cross'}
                />
                <small>
                  Your display's index pattern is {indexPatternInScope ? '' : 'not'} within the scope of the project.
                </small>
              </p>
            }
          </>}>
            <EuiFieldText
              name='name'
              onChange={(e) => {
                if (modalCreate)
                  return setModalCreate(prev => ({ ...prev, index_pattern: e.target.value }))
                return setModalUpdate(prev => ({ ...prev, index_pattern: e.target.value }))
              }}
              value={(() => {
                return modalCreate ? modalCreate.index_pattern : modalUpdate.index_pattern
              })()}
            />
          </EuiFormRow>
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          disabled={isProcessingDisplay || !indexPatternInput.trim().length || !indexPatternInScope}
          fill
          form='create-update'
          isLoading={isProcessingDisplay}
          onClick={onSubmit}
          type='submit'
        >
          {modalCreate === true ? 'Create' : 'Update'}
        </EuiButton>
        <EuiButton
          color='text'
          disabled={isProcessingDisplay}
          onClick={() => { setModalCreate(null); setModalUpdate(null) }}
        >
          Cancel
        </EuiButton>
      </EuiModalFooter>
    </EuiModal>
  )

  ////  Render  ////////////////////////////////////////////////////////////////

  const columns = useMemo(() => {
    return [
      {
        field: 'name',
        name: 'Index Pattern',
        sortable: true,
        truncateText: true,
        render: (name, doc) => {
          return <EuiLink href={`#/projects/${project._id}/displays/${doc._id}`}>
            {doc.index_pattern}
          </EuiLink>
        }
      },
      {
        field: 'fields',
        name: 'Fields',
        render: (name, doc) => {
          const fields = []
          for (var i in doc.fields)
            fields.push(
              <EuiBadge color='hollow' key={doc.fields[i]}>
                {doc.fields[i]}
              </EuiBadge>
            )
          if (!fields.length)
            return <EuiBadge color='warning' iconType='warningFilled' size='xs'>none</EuiBadge>
          return fields
        },
      },
      {
        name: 'Actions',
        actions: [
          {
            color: 'text',
            description: 'Update this display',
            icon: 'documentEdit',
            name: 'update',
            onClick: (doc) => setModalUpdate(doc),
            type: 'icon',
          },
          {
            color: 'danger',
            description: 'Delete this display',
            icon: 'trash',
            name: 'delete',
            onClick: (doc) => setModalDelete(doc),
            type: 'icon',
          }
        ],
      }
    ]
  }, [displays])

  /**
   * Button that opens the modal to create a display.
   */
  const buttonCreate = (
    <EuiButton
      fill
      iconType='plusInCircle'
      onClick={() => setModalCreate({ index_pattern: '', template: { body: '' } })}>
      Create a new display
    </EuiButton>
  )

  return (<>
    {(modalCreate || modalUpdate) && renderModalCreateUpdate()}
    {modalDelete &&
      <ModalDelete
        doc={modalDelete}
        docType='display'
        isLoading={isProcessingDisplay}
        onClose={() => setModalDelete(null)}
        onError={(err) => addToast(api.errorToast(err, { title: `Failed to delete display` }))}
        onDelete={async () => await deleteDisplay(modalDelete)}
      />
    }
    <Page title='Displays' buttons={[buttonCreate]}>
      <EuiSkeletonText isLoading={!isProjectReady} lines={10}>
        {!displays &&
          <EuiCallOut
            color='primary'
            title='Welcome!'
          >
            <EuiText>
              Create your first display to get started.
            </EuiText>
            <EuiSpacer size='m' />
            {buttonCreate}
          </EuiCallOut>
        }
        {!!displays &&
          <EuiInMemoryTable
            columns={columns}
            items={displaysList}
            pagination={true}
            responsiveBreakpoint={false}
            sorting={{
              sort: {
                field: 'name',
                direction: 'asc',
              }
            }}
            tableLayout='auto'
          />
        }
      </EuiSkeletonText>
    </Page>
  </>)
}

export default Displays