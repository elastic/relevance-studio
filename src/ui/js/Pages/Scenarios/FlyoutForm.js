import React, { useEffect, useState } from 'react'
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
import { useProjectContext } from '../../Contexts/ProjectContext'

const FlyoutForm = ({ action, doc, onClose }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const {
    project,
    isLoadingScenario,
    createScenario,
    updateScenario
  } = useProjectContext()

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
    if (!project?.params)
      return
    const _params = []
    project.params.forEach((param) => _params.push({ name: param, value: '' }))
    setForm(prev => ({ ...prev, values: _params }))
  }, [project])

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
      tags: doc.tags
    })
  }, [doc])

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onSubmit = async (e) => {
    e.preventDefault();
    const newDoc = {
      name: form.name.trim(),
      tags: (form.tags || []).sort()
    }
    if (action == 'create') {
      newDoc.values = Object.fromEntries(
        form.values.map(({ name, value }) => [name, value.trim()])
      )
      await createScenario(newDoc)
    } else if (action == 'update') {
      await updateScenario(doc._id, newDoc)
    }
    onClose()
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
          const tags = []
          options.forEach((option) => tags.push(option.key))
          setForm(prev => ({ ...prev, ['tags']: tags }))
        }}
        onCreateOption={(tag) => {
          const tags = form.tags?.concat(tag)
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
                disabled={isLoadingScenario}
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
                disabled={isLoadingScenario || isInvalidForm()}
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