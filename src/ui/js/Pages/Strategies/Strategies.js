import React, { useEffect, useMemo, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiComboBox,
  EuiFieldText,
  EuiForm,
  EuiFormRow,
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

const Strategies = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const {
    project,
    isProjectReady,
    isProcessingStrategy,
    loadAssets,
    strategies,
    createStrategy,
    updateStrategy,
    deleteStrategy
  } = useProjectContext()

  /**
   * Load (or reload) any needed assets when project is ready.
   */
  useEffect(() => {
    if (isProjectReady)
      loadAssets({ strategies: true })
  }, [project?._id])

  /**
   * Strategies as an array for the table component
   */
  const strategiesList = Object.values(strategies) || []

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

      // Create strategy and redirect to its editor
      const doc = { ...modalCreate }
      doc.name = doc.name.trim()
      const response = await createStrategy(doc)
      window.location.href = `/#/projects/${project._id}/strategies/${response.data._id}`
      return setModalCreate(null)
    } else {

      // Update display and close modal
      const doc = { ...modalUpdate }
      doc.name = doc.name.trim()
      await updateStrategy(doc)
      return setModalUpdate(null)
    }
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  /**
   * Modal to create or update a strategy.
   */
  const renderModalCreateUpdate = () => (
    <EuiModal onClose={() => { setModalCreate(null); setModalUpdate(null) }}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          {modalCreate ? 'Create a new strategy' : 'Update strategy'}
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiForm component='form' id='create-update'>
          <EuiFormRow label='Name' helpText='A descriptive name for this strategy.'>
            <EuiFieldText
              name='name'
              onChange={(e) => {
                if (modalCreate)
                  return setModalCreate(prev => ({ ...prev, name: e.target.value }))
                return setModalUpdate(prev => ({ ...prev, name: e.target.value }))
              }}
              value={(() => {
                return modalCreate ? modalCreate.name : modalUpdate.name
              })()}
            />
          </EuiFormRow>
          <EuiFormRow label='Tags' helpText='Optional tags to keep things organized.'>
            <EuiComboBox
              noSuggestions
              placeholder='Tags'
              onChange={(options) => {
                const tags = []
                options.forEach((option) => tags.push(option.key))
                if (modalCreate)
                  return setModalCreate(prev => ({ ...prev, ['tags']: tags }))
                return setModalUpdate(prev => ({ ...prev, ['tags']: tags }))
              }}
              onCreateOption={(tag) => {
                const tags = (modalCreate || modalUpdate).tags?.concat(tag)
                if (modalCreate)
                  return setModalCreate(prev => ({ ...prev, ['tags']: tags }))
                return setModalUpdate(prev => ({ ...prev, ['tags']: tags }))
              }}
              selectedOptions={(modalCreate || modalUpdate).tags?.map((tag) => ({ key: tag, label: tag }))}
            />
          </EuiFormRow>
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          disabled={isProcessingStrategy || !((modalCreate || modalUpdate).name || '').length}
          fill
          form='create-update'
          isLoading={isProcessingStrategy}
          onClick={onSubmit}
          type='submit'
        >
          Create
        </EuiButton>
        <EuiButton
          color='text'
          disabled={isProcessingStrategy}
          onClick={() => { setModalCreate(null); setModalUpdate(null) }}
        >
          Cancel
        </EuiButton>
      </EuiModalFooter>
    </EuiModal>
  )

  const columns = useMemo(() => {
    return [
      {
        field: 'name',
        name: 'Strategy',
        sortable: true,
        truncateText: true,
        render: (name, doc) => (
          <EuiLink href={`#/projects/${project._id}/strategies/${doc._id}`}>
            {doc.name}
          </EuiLink>
        )
      },
      {
        field: 'tags',
        name: 'Tags',
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
        field: 'params',
        name: 'Params',
        render: (name, doc) => {
          const params = []
          for (var i in doc.params)
            params.push(
              <EuiBadge color='hollow' key={doc.params[i]}>
                {doc.params[i]}
              </EuiBadge>
            )
          if (!params.length)
            return <EuiBadge color='warning' iconType='warningFilled' size='xs'>none</EuiBadge>
          return params
        },
      },
      {
        name: 'Actions',
        actions: [
          {
            color: 'text',
            description: 'Update this strategy',
            icon: 'documentEdit',
            name: 'update',
            onClick: (doc) => setModalUpdate(doc),
            type: 'icon',
          },
          {
            color: 'danger',
            description: 'Delete this strategy',
            icon: 'trash',
            name: 'delete',
            onClick: (doc) => setModalDelete(doc),
            type: 'icon',
          }
        ],
      }
    ]
  }, [strategies])

  /**
   * Button that opens the modal to create a strategy.
   */
  const buttonCreate = (
    <EuiButton
      fill
      iconType='plusInCircle'
      onClick={() => setModalCreate({
        name: '',
        tags: [],
        template: {
          source: {}
        }
      })}>
      Create a new strategy
    </EuiButton>
  )

  return (<>
    {(modalCreate || modalUpdate) && renderModalCreateUpdate()}
    {modalDelete &&
      <ModalDelete
        doc={modalDelete}
        docType='strategy'
        isLoading={isProcessingStrategy}
        onClose={() => setModalDelete(null)}
        onError={(err) => addToast(api.errorToast(err, { title: `Failed to delete strategy` }))}
        onDelete={async () => await deleteStrategy(modalDelete)}
      />
    }
    <Page title='Strategies' buttons={[buttonCreate]}>
      <EuiSkeletonText isLoading={!isProjectReady} lines={10}>
        {!strategies &&
          <EuiCallOut
            color='primary'
            title='Welcome!'
          >
            <EuiText>
              Create your first strategy to get started.
            </EuiText>
            <EuiSpacer size='m' />
            {buttonCreate}
          </EuiCallOut>
        }
        {!!strategies &&
          <EuiInMemoryTable
            columns={columns}
            items={strategiesList}
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

export default Strategies