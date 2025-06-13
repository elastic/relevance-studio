import React, { useEffect, useState } from 'react'
import {
  EuiButton,
  EuiButtonEmpty,
  EuiButtonGroup,
  EuiButtonIcon,
  EuiForm,
  EuiFormRow,
  EuiFieldText,
  EuiLink,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFlyout,
  EuiFlyoutBody,
  EuiFlyoutHeader,
  EuiFlyoutFooter,
  EuiInlineEditTitle,
  EuiSpacer,
  EuiText,
  EuiToolTip
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import api from '../../api'
import utils from '../../utils'

const FlyoutForm = ({ action, doc, onClose, onCreated, onUpdated }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [form, setForm] = useState({
    name: '',
    index_pattern: '',
    params: [{ name: 'text' }],
    rating_scale: 'graded'
  })
  const [formBlurs, setFormBlurs] = useState({
    name: false,
    index_pattern: false,
    rating_scale: false
  })
  const [isLoading, setIsLoading] = useState(false)

  ////  Effects  ///////////////////////////////////////////////////////////////

  // Populate form with doc if updating
  useEffect(() => {
    if (action != 'update')
      return
    setForm({
      name: doc.name,
      index_pattern: doc.index_pattern,
      params: (doc.params || []).map(p => { return { name: p }}),
      rating_scale: doc.rating_scale?.max == 1 ? 'binary' : 'graded'
    })
  }, [doc])

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onSubmit = (e) => {
    e.preventDefault();
    const newDoc = doc ? { ...doc } : {}
    newDoc.name = form.name.trim()
    newDoc.index_pattern = form.index_pattern.trim()
    newDoc.params = form.params.map(p => p.name.trim()).filter(p => p != '').sort()
    newDoc.rating_scale = {
      min: 0,
      max: form.rating_scale == 'graded' ? 4 : 1
    }
    if (action == 'create')
      return onSubmitCreate(newDoc)
    if (action == 'update')
      return onSubmitUpdate(newDoc)
  }

  const onSubmitCreate = (newDoc) => {
    (async () => {

      // Submit API request
      let response
      try {
        setIsLoading(true)
        response = await api.create_project(newDoc)
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to create project' }))
      } finally {
        setIsLoading(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Created project',
        color: 'success',
        iconType: 'check',
        text: (
          <EuiText size='xs'>
            <b>{newDoc.name}</b><br />
            <EuiText color='subdued' size='xs'>
              <small>{response.data._id}</small>
            </EuiText>
          </EuiText>
        )
      })
      newDoc._id = response.data._id
      onCreated(newDoc)
      onClose()
    })()
  }

  const onSubmitUpdate = (newDoc) => {
    (async () => {

      // Submit API request
      let response
      try {
        setIsLoading(true)
        response = await api.update_project(doc._id, newDoc)
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to create project' }))
      } finally {
        setIsLoading(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Updated project',
        color: 'success',
        iconType: 'check',
        text: (
          <EuiText size='xs'>
            <b>{newDoc.name}</b><br />
            <EuiText color='subdued' size='xs'>
              <small>{response.data._id}</small>
            </EuiText>
          </EuiText>
        )
      })
      onUpdated(newDoc)
      onClose()
    })()
  }

  ////  Form validation  ///////////////////////////////////////////////////////

  const isInvalidName = () => !form.name?.trim()
  const isInvalidIndexPattern = () => !form.index_pattern?.trim()
  const isInvalidRatingScale = () => form.rating_scale != 'graded' && form.rating_scale != 'binary'
  const isInvalidParams = () => {
    if (!form.params.length)
      return true
    for (const i in form.params)
      if (form.params[i].name?.trim())
        return false
    return true
  }
  const isInvalidForm = () => {
    return isInvalidName() || isInvalidIndexPattern() || isInvalidRatingScale() || isInvalidParams()
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderFormName = () => {
    return (
      <EuiInlineEditTitle
        heading='h2'
        inputAriaLabel='Project name'
        isInvalid={formBlurs.name && isInvalidName()}
        placeholder='Set project name'
        onBlur={(e) => setFormBlurs(prev => ({ ...prev, name: true }))}
        onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
        value={form.name}
      />
    )
  }

  const renderFormRatingScale = () => {
    return (
      <EuiButtonGroup
        color='primary'
        idSelected={form.rating_scale}
        isDisabled={action == 'update'}
        legend='Rating scale'
        onBlur={() => setFormBlurs(prev => ({ ...prev, rating_scale: true }))}
        onChange={(id) => setForm(prev => ({ ...prev, rating_scale: id }))}
        options={[
          { id: 'graded', label: 'Graded' },
          { id: 'binary', label: 'Binary' }
        ]}
      />
    )
  }

  const renderFormIndexPattern = () => {
    return (
      <EuiFieldText
        aria-label='Set index name'
        isInvalid={formBlurs.index_pattern && isInvalidIndexPattern()}
        onBlur={() => setFormBlurs(prev => ({ ...prev, index_pattern: true }))}
        onChange={(e) => setForm(prev => ({ ...prev, index_pattern: e.target.value }))}
        placeholder='Set index pattern'
        value={form.index_pattern}
      />
    )
  }

  const renderFormParams = () => {
    const rows = []
    form.params.forEach((param, i) => {
      const row = (
        <div key={i}>
          <EuiFlexGroup gutterSize='xs' responsive={false}>
            <EuiFlexItem grow>
              <EuiFieldText
                aria-label='Set param name'
                onChange={(e) => {
                  setForm(prev => {
                    const newParams = [...prev.params]
                    newParams[i] = {
                      ...newParams[i],
                      name: e.target.value
                    }
                    return { ...prev, params: newParams }
                  })
                }}
                placeholder='name'
                value={param.name}
              />
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiToolTip content='Remove param'>
                <EuiButtonIcon
                  aria-label='Remove param'
                  color='danger'
                  display='empty'
                  iconType='cross'
                  onClick={() => {
                    setForm(prev => ({
                      ...prev,
                      params: prev.params.filter((_, idx) => idx !== i)
                    }))
                  }}
                  size='m'
                />
              </EuiToolTip>
            </EuiFlexItem>
          </EuiFlexGroup>
          <EuiSpacer size='xs' />
        </div>
      )
      rows.push(row)
    })
    return (<>
      {rows}
      <EuiButton
        color={form.params.length ? 'text' : 'danger'}
        iconType='plusInCircle'
        onClick={() => {
          setForm(prev => ({
            ...prev, params: [
              ...prev.params, {
                name: ''
              }
            ]
          }))
        }}
        size='s'
      >
        <small>add param</small>
      </EuiButton>
    </>)
  }

  return (
    <EuiForm>
      <EuiFlyout hideCloseButton onClose={onClose} ownFocus>
        <EuiFlyoutHeader hasBorder>
          {renderFormName()}
        </EuiFlyoutHeader>
        <EuiFlyoutBody>
          <EuiFormRow
            helpText={action == 'create' ? `You can't change this later. We recommend "graded" for its flexibility.` : ''}
            label='Rating scale for judgements'
          >
            {renderFormRatingScale()}
          </EuiFormRow>
          <EuiSpacer />
          <EuiFormRow
            helpText={<>A comma-separated list of <EuiLink href='https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-multiple-data-streams-indices' target='_blank'>index patterns</EuiLink> to scope searches.</>}
            label='Index pattern'
          >
            {renderFormIndexPattern()}
          </EuiFormRow>
          <EuiSpacer />
          <EuiFormRow
            helpText='Named variables for scenarios and strategies.'
            label='Params'
          >
            {renderFormParams()}
          </EuiFormRow>
        </EuiFlyoutBody>
        <EuiFlyoutFooter>
          <EuiFlexGroup justifyContent='spaceBetween'>
            <EuiFlexItem grow={false}>
              <EuiButtonEmpty
                disabled={isLoading}
                flush='left'
                iconType='cross'
                onClick={onClose}
              >
                Cancel
              </EuiButtonEmpty>
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiButton
                color='primary'
                disabled={isLoading || isInvalidForm()}
                fill
                onClick={onSubmit}
                type='submit'
              >
                {action == 'create' ? 'Create' : 'Save'}
              </EuiButton>
            </EuiFlexItem>
          </EuiFlexGroup>
        </EuiFlyoutFooter>
      </EuiFlyout>
    </EuiForm>
  )
}

export default FlyoutForm