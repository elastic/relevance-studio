import React, { useEffect, useState } from 'react'
import {
  EuiFlyout,
  EuiFlyoutBody,
  EuiFlyoutHeader,
  EuiFormRow,
  EuiListGroup,
  EuiListGroupItem,
  EuiSkeletonText,
  EuiSpacer,
  EuiSuperSelect,
  EuiSwitch,
  EuiText,
} from '@elastic/eui'
import client from '../../client'
import utils from '../../utils'

const FlyoutSearches = (props) => {

  ////  Props  /////////////////////////////////////////////////////////////////

  const close = props.close
  const indexOptions = props.indexOptions
  const indices = props.indices
  const indexSelected = props.indexSelected
  const loading = props.loading

  ////  State  /////////////////////////////////////////////////////////////////

  const [fieldsSelected, setFieldsSelected] = useState({})

  /**
   * Create field options from selected index
   */
  useEffect(() => {
    if (!indexSelected)
      return
    const ignoredTypes = ['dense_vector', 'semantic_text']
    const _fieldsSelected = {}
    for (const [field, type] of Object.entries(indices[indexSelected]['fields'])) {
      if (ignoredTypes.includes(type))
        continue
      _fieldsSelected[field] = true
    }
    setFieldsSelected(_fieldsSelected)
  }, [indexSelected])

  /**
   * Handle toggling of displayed fields
   */
  const toggleField = (e) => {
    e.stopPropagation()
    const field = e.target.value || e.target.innerText // EuiSwitch || EuiListGroupItem
    if (field in fieldsSelected)
      setFieldsSelected(prev => {
        const newFields = { ...prev }
        delete newFields[field]
        return newFields
      })
    else
      setFieldsSelected(prev => ({ ...prev, [field]: true, }))
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderFieldToggles = () => {
    const fields = []
    for (const field in indices[indexSelected]['fields']) {
      fields.push(
        <EuiListGroupItem
          label={<>
            <EuiSwitch
              checked={!!fieldsSelected[field]}
              label={
                <EuiText
                  color={!!fieldsSelected[field] ? 'text' : 'subdued'}
                  size='s'
                  style={{ fontWeight: !!fieldsSelected[field] ? 600 : 200 }}
                >
                  {field}
                </EuiText>
              }
              mini
              onChange={toggleField}
              style={{ top: '6px' }}
              tabIndex={-1}
              value={field}
            />
          </>}
          onClick={toggleField}
        />
      )
    }
    return fields
  }

  return (
    <EuiFlyout ownFocus onClose={close}>
      <EuiFlyoutHeader hasBorder>
        <EuiText size='m'>
          <h2>Adjust searches</h2>
        </EuiText>
      </EuiFlyoutHeader>
      <EuiFlyoutBody>

        {/* Select index */}
        <EuiFormRow label='Select index'>
          <EuiSuperSelect
            hasDividers
            isLoading={loading}
            itemLayoutAlign='top'
            onChange={(index) => setIndexSelected(index)}
            options={indexOptions}
            placeholder='Indices'
            valueOfSelected={indexSelected}
          />
        </EuiFormRow>

        <EuiSpacer size='m' />

        {/* Toggle fields */}
        <EuiFormRow label='Select fields to include in results'>
          <EuiSkeletonText lines={10} isLoading={loading}>
            {!!indices[indexSelected] &&
              <EuiListGroup bordered flush gutterSize='none' size='xs'>
                {renderFieldToggles()}
              </EuiListGroup>
            }
          </EuiSkeletonText>
        </EuiFormRow>
      </EuiFlyoutBody>
    </EuiFlyout>
  )
}

export default FlyoutSearches