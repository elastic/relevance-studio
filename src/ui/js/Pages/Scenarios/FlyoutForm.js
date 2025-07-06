import { useEffect, useState } from 'react'
import {
  EuiButton,
  EuiButtonEmpty,
  EuiComboBox,
  EuiFieldText,
  EuiForm,
  EuiFormRow,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFlyout,
  EuiFlyoutBody,
  EuiFlyoutHeader,
  EuiFlyoutFooter,
  EuiInlineEditTitle,
  EuiSpacer,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { usePageResources, useResources } from '../../Contexts/ResourceContext'
import api from '../../api'
import utils from '../../utils'

const FlyoutForm = ({
  action,
  doc,
  isProcessing,
  onClose,
  onSuccess,
  setIsProcessing
}) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const { project } = usePageResources()
  const isReady = useResources().hasResources(['project'])

  ////  State  /////////////////////////////////////////////////////////////////

  const [form, setForm] = useState({
    name: '',
    values: [],
    tags: []
  })
  const [formBlurs, setFormBlurs] = useState({
    name: false,
    values: false
  })

  ////  Effects  ///////////////////////////////////////////////////////////////

  // Initialize params from project
  useEffect(() => {
    if (!isReady)
      return
    const _params = []
    project.params.forEach((param) => _params.push({ name: param, value: '' }))
    setForm(prev => ({ ...prev, values: _params }))
  }, [isReady])

  // Populate form with doc if updating
  useEffect(() => {
    if (action != 'update')
      return
    setForm({
      name: doc.name,
      values: Object.entries(doc.values || {}).map(([param, value]) => ({
        name: param,
        value: value
      })),
      tags: doc.tags || []
    })
  }, [doc])

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onSubmit = async (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();
    let response
    try {
      setIsProcessing(true)
      const newDoc = {
        name: form.name.trim(),
        tags: (form.tags || []).sort()
      }
      if (action == 'create') {
        newDoc.values = Object.fromEntries(
          form.values
            .map(({ name, value }) => [name, String(value).trim()])
            .filter(([, trimmed]) => trimmed !== "")
        )
        response = await api.scenarios_create(project._id, newDoc)
      } else if (action == 'update') {
        response = await api.scenarios_update(project._id, doc._id, newDoc)
      }
      if (response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast(utils.toastDocCreateUpdateDelete(action, 'scenario', doc._id || response.data._id))
      if (onSuccess)
        onSuccess()
      if (onClose)
        onClose()
    } catch (e) {
      return addToast(api.errorToast(e, { title: `Failed to ${action} scenario` }))
    } finally {
      setIsProcessing(false)
    }
  }

  ////  Form validation  ///////////////////////////////////////////////////////

  const isInvalidName = () => !form.name?.trim()
  const isInvalidValues = () => {
    if (!form.values.length)
      return true
    for (const i in form.values)
      if (form.values[i].value?.trim())
        return false
    return true
  }
  const isInvalidForm = () => {
    return isInvalidName() || isInvalidValues()
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderFormName = () => {
    return (
      <EuiInlineEditTitle
        heading='h2'
        inputAriaLabel='Scenario name'
        isInvalid={formBlurs.name && isInvalidName()}
        placeholder='Set scenario name'
        onBlur={(e) => setFormBlurs(prev => ({ ...prev, name: true }))}
        onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
        value={form.name}
      />
    )
  }

  const renderFormValues = () => {
    const rows = []
    form.values.forEach((value, i) => {
      const row = (
        <div key={i}>
          <EuiFieldText
            aria-label='Set value name'
            disabled={action == 'update' ? true : false}
            onChange={(e) => {
              setForm(prev => {
                const newValues = [...prev.values]
                newValues[i] = {
                  ...newValues[i],
                  value: e.target.value
                }
                return { ...prev, values: newValues }
              })
            }}
            placeholder='value'
            prepend={value.name}
            value={value.value}
          />
          <EuiSpacer size='xs' />
        </div>
      )
      rows.push(row)
    })
    return (<>
      {rows}
    </>)
  }

  const renderFormTags = () => {
    return (
      <EuiComboBox
        noSuggestions
        placeholder='Tags'
        onChange={(options) => {
          const tags = options.map((option) => option.key)
          setForm(prev => ({ ...prev, tags: [...tags] }))
        }}
        onCreateOption={(tag) => {
          const tags = [...(form.tags || []), tag]
          setForm(prev => ({ ...prev, ['tags']: tags }))
        }}
        selectedOptions={form.tags?.map((tag) => ({ key: tag, label: tag }))}
      />
    )
  }

  return (
    <EuiForm>
      <EuiFlyout hideCloseButton onClose={onClose} ownFocus>
        <EuiFlyoutHeader hasBorder>
          {renderFormName()}
        </EuiFlyoutHeader>
        <EuiFlyoutBody>
          <EuiFormRow
            helpText='These params will be passed to strategies that implement them.'
            label='Params'
          >
            {renderFormValues()}
          </EuiFormRow>
          <EuiFormRow label='Tags' helpText='Optional tags to keep things organized.'>
            {renderFormTags()}
          </EuiFormRow>
        </EuiFlyoutBody>
        <EuiFlyoutFooter>
          <EuiFlexGroup justifyContent='spaceBetween'>
            <EuiFlexItem grow={false}>
              <EuiButtonEmpty
                disabled={isProcessing}
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
                disabled={isProcessing || isInvalidForm()}
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