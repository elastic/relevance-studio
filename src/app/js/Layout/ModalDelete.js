import React, { useState } from 'react'
import {
  EuiButton,
  EuiForm,
  EuiModal,
  EuiModalBody,
  EuiModalFooter,
  EuiModalHeader,
  EuiModalHeaderTitle,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../Contexts/AppContext'
import { useProjectContext } from '../Contexts/ProjectContext'
import api from '../api'
import utils from '../utils'

const ModalDelete = ({ doc, docType, onClose, onDeleted }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const { project } = useProjectContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [isLoading, setIsLoading] = useState(false)

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onSubmit = async (e) => {
    e.preventDefault();
    
    // Submit API request
    let response
    try {
      setIsLoading(true)
      if (docType == 'project')
        response = await api.delete_project(doc._id)
      else if (docType == 'display')
        response = await api.delete_display(project._id, doc._id)
      else if (docType == 'scenario')
        response = await api.delete_scenario(project._id, doc._id)
      else if (docType == 'strategy')
        response = await api.delete_strategy(project._id, doc._id)
      else if (docType == 'evaluation')
        response = await api.delete_evaluation(project._id, doc._id)
    } catch (err) {
      return addToast(api.errorToast(err, { title: `Failed to delete ${docType}` }))
    } finally {
      setIsLoading(false)
    }

    // Handle API response
    if (response.status < 200 && response.status > 299)
      return addToast(utils.toastClientResponse(response))
    addToast({
      title: `Deleted ${docType}`,
      color: 'success',
      iconType: 'check',
      text: (
        <EuiText size='xs'>
          <b>{doc.name}</b><br />
          <EuiText color='subdued' size='xs'>
            <small>{doc._id}</small>
          </EuiText>
        </EuiText>
      )
    })
    onDeleted()
    onClose()
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  return (
    <EuiModal onClose={onClose}>
      <EuiModalHeader>
        <EuiModalHeaderTitle>
          Delete <b>{docType}</b>?
        </EuiModalHeaderTitle>
      </EuiModalHeader>
      <EuiModalBody>
        <EuiForm component='form' id='delete'>
          <EuiText color='subdued' size='xs'>
            _id:<br /><b>{doc._id}</b>
          </EuiText>
          <EuiSpacer size='m' />
          <EuiText>This action can't be undone.</EuiText>
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          color='danger'
          disabled={isLoading}
          fill
          form='modal-delete'
          isLoading={isLoading}
          onClick={onSubmit}
          type='submit'
        >
          Delete
        </EuiButton>
        <EuiButton
          color='text'
          disabled={isLoading}
          onClick={onClose}
        >
          Cancel
        </EuiButton>
      </EuiModalFooter>
    </EuiModal>
  )
}

export default ModalDelete