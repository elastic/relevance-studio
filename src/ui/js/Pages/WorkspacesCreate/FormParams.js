/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  EuiButton,
  EuiButtonIcon,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFieldText,
  EuiFormRow,
  EuiPanel,
  EuiSpacer,
  EuiSuperSelect,
  EuiTextArea,
  EuiToolTip,
} from '@elastic/eui'

const FormParams = ({ onAdd, onChange, onRemove, params }) => {

  const typeOptions = [
    {
      inputDisplay: 'Text',
      value: 'text',
    },
    {
      inputDisplay: 'Number',
      value: 'number',
    },
  ]

  const renderParams = () => {
    const rows = []
    params.forEach((param, i) => {
      const row = (
        <>
          <EuiPanel key={i} paddingSize='s'>
            <EuiPanel color='subdued' paddingSize='s'>
              <EuiFlexGroup gutterSize='m' responsive={false}>

                {/* Name */}
                <EuiFlexItem grow={7}>
                  <EuiFormRow label='Name'>
                    <EuiFieldText
                      aria-label='Parameter name'
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
                  </EuiFormRow>
                </EuiFlexItem>

                {/* Type */}
                <EuiFlexItem grow={3}>
                  <EuiFormRow label='Type'>
                    <EuiSuperSelect
                      aria-label='Parameter type'
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
                      options={typeOptions}
                      valueOfSelected={param.type}
                    />
                  </EuiFormRow>
                </EuiFlexItem>
              </EuiFlexGroup>

              <EuiSpacer size='m' />

              {/* Description */}
              <EuiFormRow label='Description'>
                <EuiTextArea
                  aria-label='Parameter description'
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
                  value={param.description}
                  style={{ height: '45px', minHeight: '45px' }}
                />
              </EuiFormRow>

              {/* Remove */}
              <div style={{ position: 'absolute', right: '-20px', top: '-20px', zIndex: 1 }}>
                <EuiToolTip content='Remove parameter'>
                  <EuiButtonIcon
                    aria-label='Remove parameter'
                    color='text'
                    display='base'
                    iconSize='s'
                    iconType='cross'
                    onClick={() => {
                      setForm(prev => ({
                        ...prev,
                        params: prev.params.filter((_, idx) => idx !== i)
                      }))
                    }}
                    size='xs'
                    style={{ borderRadius: '20px' }}
                  />
                </EuiToolTip>
              </div>
            </EuiPanel>
          </EuiPanel>
          <EuiSpacer />
        </>
      )
      rows.push(row)
    })
    return rows
  }

  return (
    <EuiFormRow fullWidth style={{ width: '600px' }}>
      <>
        {renderParams()}
        <EuiSpacer size='s' />
        <div style={{ textAlign: 'center' }}>
          <EuiButton
            color={params.length ? 'text' : 'danger'}
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
            <small>Add another</small>
          </EuiButton>
        </div>
      </>
    </EuiFormRow>
  )
}

export default FormParams