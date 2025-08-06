/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

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
import api from '../api'
import utils from '../utils'

const ModalDelete = ({
  description,
  doc,
  docType,
  isProcessing,
  onClose,
  onDelete,
  onError,
  onSuccess,
  setIsProcessing,
}) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onSubmit = async (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();
    try {
      setIsProcessing(true)
      try {
        await onDelete()
      } catch (e) {
        if (onError)
          return onError(e)
        else
          return addToast(api.errorToast(e, { title: `Failed to delete ${docType}` }))
      }
      addToast(utils.toastDocCreateUpdateDelete('delete', docType, doc._id, doc))
      if (onSuccess)
        onSuccess()
      if (onClose)
        onClose()
    } catch (e) {
      throw (e)
    } finally {
      setIsProcessing(false)
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
          {!description && <EuiText>This action can't be undone.</EuiText>}
          {!!description && description}
        </EuiForm>
      </EuiModalBody>
      <EuiModalFooter>
        <EuiButton
          color='danger'
          disabled={isProcessing}
          fill
          form='modal-delete'
          isLoading={isProcessing}
          onClick={onSubmit}
          type='submit'
        >
          Delete
        </EuiButton>
        <EuiButton
          color='text'
          disabled={isProcessing}
          onClick={onClose}
        >
          Cancel
        </EuiButton>
      </EuiModalFooter>
    </EuiModal>
  )
}

export default ModalDelete