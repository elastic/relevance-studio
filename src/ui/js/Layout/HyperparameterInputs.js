/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useRef, useState } from 'react'
import {
  EuiAccordion,
  EuiBadge,
  EuiButtonEmpty,
  EuiFieldNumber,
  EuiFieldText,
  EuiFlexGroup,
  EuiFlexItem,
  EuiPanel,
  EuiSwitch,
  EuiText,
} from '@elastic/eui'
import { inputsDiffer } from '../hyperparameters'

const ellipsis = { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }

/**
 * An accordion of inputs, one row per hyperparameter, to choose the values for
 * a single search.
 *
 * `inputs` comes from `syncInputs` and `parsed` from `parseInputs`. Each input
 * starts at the promoted value. A boolean is a switch, and any other value is a
 * free-form field that the valid testable values don't constrain. Each row stays on one
 * line. The accordion opens when hyperparameters first appear, and closes when
 * there are none.
 */
const HyperparameterInputs = ({
  definitions = [],
  inputs = {},
  parsed = { errors: {}, warnings: {} },
  onChange,
  onReset,
  disabled = false,
  idPrefix = 'hp-input',
  maxHeight = '30vh',
}) => {
  const items = definitions.filter((hp) => hp.name && inputs[hp.name])
  const [isOpen, setIsOpen] = useState(items.length > 0)
  const previousCount = useRef(items.length)

  useEffect(() => {
    if (previousCount.current === 0 && items.length > 0)
      setIsOpen(true)
    else if (items.length === 0)
      setIsOpen(false)
    previousCount.current = items.length
  }, [items.length])

  const setRaw = (name, raw) => onChange({ ...inputs, [name]: { ...inputs[name], raw } })

  const renderControl = (hp) => {
    const input = inputs[hp.name]
    const id = `${idPrefix}-${hp.name}`
    const isInvalid = Boolean(parsed.errors?.[hp.name])
    if (hp.type === 'boolean') {
      return (
        <EuiSwitch
          checked={input.raw === true}
          compressed
          disabled={disabled}
          id={id}
          label={<small>{String(input.raw === true)}</small>}
          onChange={(e) => setRaw(hp.name, e.target.checked)}
        />
      )
    }
    if (hp.type === 'number') {
      return (
        <EuiFieldNumber
          aria-label={hp.name}
          compressed
          disabled={disabled}
          fullWidth
          id={id}
          isInvalid={isInvalid}
          onChange={(e) => setRaw(hp.name, e.target.value)}
          step='any'
          value={input.raw}
        />
      )
    }
    return (
      <EuiFieldText
        aria-label={hp.name}
        compressed
        disabled={disabled}
        fullWidth
        id={id}
        isInvalid={isInvalid}
        onChange={(e) => setRaw(hp.name, e.target.value)}
        value={input.raw}
      />
    )
  }

  // One line of text after the control: an error or a warning
  const renderNote = (hp) => {
    const error = parsed.errors?.[hp.name]
    const warning = parsed.warnings?.[hp.name]
    let color = 'subdued'
    let text = null
    if (error) {
      color = 'danger'
      text = error
    } else if (warning) {
      color = 'warning'
      text = warning
    }
    if (!text)
      return null
    return (
      <EuiText color={color} size='xs' style={ellipsis} title={text}>
        <small>{text}</small>
      </EuiText>
    )
  }

  const renderRow = (hp) => (
    <EuiFlexGroup alignItems='center' gutterSize='s' key={hp.name} responsive={false} style={{ marginBottom: '4px' }}>
      <EuiFlexItem grow={false} style={{ width: '130px' }}>
        <EuiText size='xs' style={ellipsis} title={`${hp.name} (${hp.type})`}>
          <b>{hp.name}</b>
        </EuiText>
      </EuiFlexItem>
      <EuiFlexItem grow={false} style={{ width: '64px' }}>
        <EuiBadge color='hollow'><small>{hp.type}</small></EuiBadge>
      </EuiFlexItem>
      <EuiFlexItem grow={false} style={{ width: '140px' }}>
        {renderControl(hp)}
      </EuiFlexItem>
      <EuiFlexItem grow style={{ minWidth: 0 }}>
        {renderNote(hp)}
      </EuiFlexItem>
    </EuiFlexGroup>
  )

  return (
    <EuiPanel color='subdued' hasBorder={false} hasShadow={false} paddingSize='s'>
      <EuiAccordion
        buttonContent={
          <EuiText size='s'>
            Hyperparameters{' '}
            <EuiBadge color='hollow'><small>{items.length}</small></EuiBadge>
          </EuiText>
        }
        extraAction={
          inputsDiffer(definitions, inputs)
            ? (
              <EuiButtonEmpty
                color='text'
                disabled={disabled}
                iconType='refresh'
                onClick={onReset}
                size='xs'
              >
                Reset to promoted values
              </EuiButtonEmpty>
            )
            : undefined
        }
        forceState={isOpen ? 'open' : 'closed'}
        id={`${idPrefix}-accordion`}
        onToggle={setIsOpen}
        paddingSize='s'
      >
        {items.length === 0
          ? <EuiText color='subdued' size='xs'><small>This strategy has no hyperparameters.</small></EuiText>
          : <div style={{ maxHeight, overflowY: 'auto' }}>{items.map(renderRow)}</div>
        }
      </EuiAccordion>
    </EuiPanel>
  )
}

export default HyperparameterInputs
