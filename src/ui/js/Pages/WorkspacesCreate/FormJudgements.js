/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useState } from 'react'
import {
  euiPaletteForStatus,
  EuiButton,
  EuiFieldNumber,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFormRow,
  EuiFormControlLayoutDelimited,
  EuiMarkdownEditor,
  EuiMarkdownFormat,
  EuiPanel,
  EuiRange,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'

const FormJudgements = ({ description = '', max = 4, min = 0, onChangeMax, onChangeMin, onChangeDescription }) => {

  const [isEditing, setIsEditing] = useState(false)
  const [rating, setRating] = useState(max)

  const colorBands = (min, max, rating) => euiPaletteForStatus(max - min + 1).reverse()[rating]
  const ticks = () => {
    const _ticks = []
    for (var i = min; i <= max; i++) {
      _ticks.push({
        label: <EuiText color='subdued' size='xs'><small>{i}</small></EuiText>,
        value: i
      })
    }
    return _ticks
  }

  const renderRatingScale = () => {
    return (
      <EuiFlexGroup gutterSize='m' responsive={false} style={{ width: '600px' }}>
        <EuiFlexItem grow={5}>
          <EuiFormRow>
            <EuiFormControlLayoutDelimited
              prepend='Min'
              append='Max'
              startControl={
                <EuiFieldNumber
                  controlOnly
                  min={0}
                  onChange={(e) => {
                    onChangeMin(e.target.value)
                  }}
                  step={1}
                  value={min}
                />
              }
              endControl={
                <EuiFieldNumber
                  autoFocus
                  controlOnly
                  max={10}
                  min={1}
                  onChange={(e) => {
                    onChangeMax(e.target.value)
                    setRating(e.target.value)
                  }}
                  step={1}
                  value={max}
                />
              }
            />
          </EuiFormRow>
        </EuiFlexItem>
        <EuiFlexItem grow={5}>
          <EuiFormRow>
            <EuiPanel
              className='judgement-card-range-slider'
              color='transparent'
              hasBorder={false}
              hasShadow={false}
              paddingSize='none'
              style={{
                borderTopLeftRadius: 0,
                borderTopRightRadius: 0,
                marginTop: '-1px',
              }}
            >
              <div style={{ marginTop: '5px' }}>
                <EuiRange
                  compressed
                  fullWidth
                  min={min}
                  max={max}
                  levels={rating >= 0 ? [
                    {
                      color: colorBands(min, max, rating),
                      min: min,
                      max: max
                    }
                  ] : [
                    {
                      color: 'text'
                    }
                  ]}
                  onChange={(e) => setRating(e.target.value)}
                  showRange
                  showTicks
                  step={1}
                  ticks={ticks()}
                  value={rating || 0}
                />
              </div>
            </EuiPanel>
          </EuiFormRow>
        </EuiFlexItem>
      </EuiFlexGroup>
    )
  }

  const renderDescription = () => (
    <>

      {/* Display the description without the editor controls */}
      {!isEditing &&
        <EuiPanel color='transparent' hasBorder={true}>
          <EuiButton
            onClick={() => setIsEditing(true)}
            size='s'
            style={{
              position: 'absolute',
              right: '5px',
              top: '5px'
            }}
          >
            Edit
          </EuiButton>
          <EuiMarkdownFormat>
            {description}
          </EuiMarkdownFormat>
        </EuiPanel>
      }

      {/* Display the editor */}
      {!!isEditing &&
        <EuiMarkdownEditor
          aria-label='Description'
          class='editor'
          height={215}
          onChange={onChangeDescription}
          style={{ width: '600px' }}
          value={description}
          uiPlugins={[]}
        />
      }
    </>
  )

  return (
    <EuiFormRow fullWidth>
      <>
        {renderRatingScale()}
        <EuiSpacer size='m' />
        {renderDescription()}
      </>
    </EuiFormRow>
  )
}

export default FormJudgements