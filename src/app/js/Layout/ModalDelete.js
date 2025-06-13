import React from 'react'
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

const ModalDelete = ({ doc, docType, isLoading, onClose, onDelete, onDeleted, onError }) => {

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onSubmit = async (e) => {
    e.preventDefault();
    try {
      try {
        await onDelete()
      } catch (e) {
        if (onError)
          return onError(e)
        throw (e)
      }
      if (onDeleted)
        onDeleted(doc)
      if (onClose)
        onClose()
    } catch (e) {
      throw (e)
    }
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