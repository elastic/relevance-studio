/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  EuiButtonGroup,
  EuiComboBox,
  EuiFieldNumber,
  EuiFlexGroup,
  EuiFlexItem,
  EuiText,
} from '@elastic/eui'
import { formatValue, parseValue, validateTestableValues } from '../hyperparameters'

const numberOrUndefined = (text) => {
  if (text === '' || text === null || text === undefined)
    return undefined
  const n = Number(text)
  return Number.isFinite(n) ? n : undefined
}

/**
 * Edit the valid testable values of a strategy's hyperparameter: the values
 * a benchmark may test. A range (numbers only) can leave either bound open,
 * such as a boost with a minimum of 0. A set lists the values.
 *
 * A boolean always has the testable values true and false, so it needs no
 * editor.
 */
const TestableValuesEditor = ({
  type,
  value,
  onChange,
  idPrefix = 'testable',
}) => {
  const kinds = []
  if (type === 'number')
    kinds.push({ id: 'range', label: 'Range' })
  kinds.push({ id: 'set', label: 'Set' })

  const kind = value?.type || (type === 'number' ? 'range' : 'set')
  const error = validateTestableValues(type, value)

  const changeKind = (id) => {
    if (id === 'set')
      return onChange({ type: 'set', values: [] })
    return onChange({ type: 'range' })
  }

  const renderRange = () => (
    <EuiFlexGroup gutterSize='xs' responsive={false}>
      <EuiFlexItem>
        <EuiFieldNumber
          aria-label='Minimum'
          compressed
          onChange={(e) => onChange({ ...value, min: numberOrUndefined(e.target.value) })}
          placeholder='No minimum'
          prepend={<small>Min</small>}
          step='any'
          value={value?.min ?? ''}
        />
      </EuiFlexItem>
      <EuiFlexItem>
        <EuiFieldNumber
          aria-label='Maximum'
          compressed
          onChange={(e) => onChange({ ...value, max: numberOrUndefined(e.target.value) })}
          placeholder='No maximum'
          prepend={<small>Max</small>}
          step='any'
          value={value?.max ?? ''}
        />
      </EuiFlexItem>
    </EuiFlexGroup>
  )

  const renderSet = () => {
    const selected = (value?.values || []).map((v) => ({ label: formatValue(v) || String(v), value: v }))
    return (
      <EuiComboBox
        aria-label='Values'
        compressed
        fullWidth
        isClearable
        noSuggestions
        onChange={(opts) => onChange({ type: 'set', values: opts.map((o) => o.value) })}
        onCreateOption={(text) => {
          const parsed = parseValue(type, type === 'string' ? text : text.trim())
          if (parsed === undefined)
            return false
          if ((value?.values || []).some((v) => v === parsed))
            return
          onChange({ type: 'set', values: [...(value?.values || []), parsed] })
        }}
        options={[]}
        placeholder={`Type a ${type} value and press Enter`}
        selectedOptions={selected}
      />
    )
  }

  return (
    <div>
      {kinds.length > 1 &&
        <EuiButtonGroup
          buttonSize='compressed'
          idSelected={`${idPrefix}-${kind}`}
          isFullWidth
          legend='Valid testable values'
          onChange={(id) => changeKind(id.replace(`${idPrefix}-`, ''))}
          options={kinds.map((k) => ({ id: `${idPrefix}-${k.id}`, label: k.label }))}
        />
      }
      {kind === 'range' && <div style={{ marginTop: kinds.length > 1 ? '4px' : 0 }}>{renderRange()}</div>}
      {kind === 'set' && <div style={{ marginTop: kinds.length > 1 ? '4px' : 0 }}>{renderSet()}</div>}
      {error &&
        <EuiText color='danger' size='xs' style={{ marginTop: '4px' }}>
          <small>{error}</small>
        </EuiText>
      }
    </div>
  )
}

export default TestableValuesEditor
