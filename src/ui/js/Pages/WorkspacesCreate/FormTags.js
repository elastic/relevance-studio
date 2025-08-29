/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  EuiButton,
  EuiButtonIcon,
  EuiColorPicker,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFieldText,
  EuiFormRow,
  EuiPanel,
  EuiSpacer,
  EuiSuperSelect,
  EuiTextArea,
  EuiToolTip,
  useColorPickerState,
} from '@elastic/eui'

const FormTags = ({ onAdd, onChange, onRemove, tags }) => {

  const renderTags = () => {
    const rows = []
    tags.forEach((tag, i) => {
      const row = (
        <>
          <EuiPanel key={i} paddingSize='s'>
            <EuiPanel color='subdued' paddingSize='s'>
              <EuiFlexGroup gutterSize='m' responsive={false}>

                {/* Name */}
                <EuiFlexItem grow={7}>
                  <EuiFormRow label='Name'>
                    <EuiFieldText
                      aria-label='Tag name'
                      onChange={(e) => {
                        setForm(prev => {
                          const newTags = [...prev.tags]
                          newTags[i] = {
                            ...newTags[i],
                            name: e.target.value
                          }
                          return { ...prev, tags: newTags }
                        })
                      }}
                      placeholder='name'
                      value={tag.name}
                    />
                  </EuiFormRow>
                </EuiFlexItem>

                {/* Color */}
                <EuiFlexItem grow={3}>
                  <EuiFormRow label='Color'>
                    <EuiColorPicker
                      onChange={() => {}}
                      color={tag.color}
                    />
                  </EuiFormRow>
                </EuiFlexItem>
              </EuiFlexGroup>

              <EuiSpacer size='m' />

              {/* Description */}
              <EuiFormRow label='Description'>
                <EuiTextArea
                  aria-label='Tag description'
                  onChange={(e) => {
                    setForm(prev => {
                      const newTags = [...prev.tags]
                      newTags[i] = {
                        ...newTags[i],
                        name: e.target.value
                      }
                      return { ...prev, tags: newTags }
                    })
                  }}
                  placeholder='name'
                  value={tag.description}
                  style={{ height: '45px', minHeight: '45px' }}
                />
              </EuiFormRow>

              {/* Remove */}
              <div style={{ position: 'absolute', right: '-20px', top: '-20px', zIndex: 1 }}>
                <EuiToolTip content='Remove tag'>
                  <EuiButtonIcon
                    aria-label='Remove tag'
                    color='text'
                    display='base'
                    iconSize='s'
                    iconType='cross'
                    onClick={() => {
                      setForm(prev => ({
                        ...prev,
                        tags: prev.tags.filter((_, idx) => idx !== i)
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
        {renderTags()}
        <EuiSpacer size='s' />
        <div style={{ textAlign: 'center' }}>
          <EuiButton
            color={tags.length ? 'text' : 'danger'}
            iconType='plusInCircle'
            onClick={() => {
              setForm(prev => ({
                ...prev, tags: [
                  ...prev.tags, {
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

export default FormTags