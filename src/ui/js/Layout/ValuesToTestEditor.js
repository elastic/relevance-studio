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
  EuiSelect,
  EuiSwitch,
  EuiText,
} from '@elastic/eui'
import {
  DEFAULT_POINTS_PER_RANGE,
  formatValue,
  gridValues,
  parseValue,
  validateValuesToTest,
} from '../hyperparameters'

const numberOrUndefined = (text) => {
  if (text === '' || text === null || text === undefined)
    return undefined
  const n = Number(text)
  return Number.isFinite(n) ? n : undefined
}

const isSet = (value) => value !== undefined && value !== null

const MAX_PREVIEW = 12

/**
 * Edit the values a benchmark tests for a hyperparameter: a finite range
 * (numbers only) or a set. The values must stay within the hyperparameter's
 * valid testable values (`testable`). Grid search takes a range's `step` or
 * `count` of points. Random search samples the range, snapped to the `step`.
 * A range without either gets `pointsPerRange` grid points. A preview lists
 * the grid values, so a value that suits a whole-number parameter shows up
 * before the run.
 */
const ValuesToTestEditor = ({
  type,
  testable,
  value,
  onChange,
  pointsPerRange = DEFAULT_POINTS_PER_RANGE,
  idPrefix = 'values-to-test',
  disabled = false,
}) => {
  const canRange = type === 'number' && testable?.type !== 'set'
  const kinds = []
  if (canRange)
    kinds.push({ id: 'range', label: 'Range' })
  kinds.push({ id: 'set', label: 'Set' })

  const kind = value?.type || kinds[0].id
  const error = validateValuesToTest(type, testable, value)

  const changeKind = (id) => {
    if (id === 'set') {
      const values = type === 'boolean'
        ? [true, false]
        : (testable?.type === 'set' ? [...testable.values] : [])
      return onChange({ type: 'set', values })
    }
    return onChange({ type: 'range', min: testable?.min, max: testable?.max, log: false })
  }

  const patch = (fields) => onChange({ ...value, ...fields })

  const renderRange = () => {
    const mode = isSet(value.step) ? 'step' : (isSet(value.count) ? 'count' : 'default')
    const preview = (() => {
      if (error)
        return null
      try {
        const values = gridValues({
          type: 'number',
          promoted_value: 0,
          values_to_test: { ...value, count: isSet(value.step) ? undefined : (value.count ?? pointsPerRange) },
        })
        const shown = values.slice(0, MAX_PREVIEW).map(formatValue).join(', ')
        return `${shown}${values.length > MAX_PREVIEW ? ', ...' : ''} (${values.length})`
      } catch (e) {
        return null
      }
    })()
    return (
      <>
        <EuiFlexGroup gutterSize='xs' responsive={false}>
          <EuiFlexItem>
            <EuiFieldNumber
              aria-label='Minimum'
              compressed
              disabled={disabled}
              isInvalid={!Number.isFinite(value.min)}
              onChange={(e) => patch({ min: numberOrUndefined(e.target.value) })}
              prepend={<small>Min</small>}
              step='any'
              value={value.min ?? ''}
            />
          </EuiFlexItem>
          <EuiFlexItem>
            <EuiFieldNumber
              aria-label='Maximum'
              compressed
              disabled={disabled}
              isInvalid={!Number.isFinite(value.max)}
              onChange={(e) => patch({ max: numberOrUndefined(e.target.value) })}
              prepend={<small>Max</small>}
              step='any'
              value={value.max ?? ''}
            />
          </EuiFlexItem>
        </EuiFlexGroup>
        <EuiFlexGroup alignItems='center' gutterSize='xs' responsive={false} style={{ marginTop: '4px' }}>
          <EuiFlexItem grow={false} style={{ width: '150px' }}>
            <EuiSelect
              aria-label='Grid resolution'
              compressed
              disabled={disabled}
              onChange={(e) => {
                const next = e.target.value
                if (next === 'step')
                  patch({ step: 1, count: undefined })
                else if (next === 'count')
                  patch({ count: pointsPerRange, step: undefined })
                else
                  patch({ step: undefined, count: undefined })
              }}
              options={[
                { value: 'default', text: `Default (${pointsPerRange} points)` },
                { value: 'step', text: 'Step', disabled: Boolean(value.log) },
                { value: 'count', text: 'Count' },
              ]}
              value={mode}
            />
          </EuiFlexItem>
          <EuiFlexItem>
            {mode !== 'default' &&
              <EuiFieldNumber
                aria-label={mode === 'step' ? 'Step' : 'Number of values'}
                compressed
                disabled={disabled}
                min={mode === 'count' ? 2 : undefined}
                onChange={(e) => patch(mode === 'step'
                  ? { step: numberOrUndefined(e.target.value) }
                  : { count: numberOrUndefined(e.target.value) })}
                step={mode === 'count' ? 1 : 'any'}
                value={(mode === 'step' ? value.step : value.count) ?? ''}
              />
            }
          </EuiFlexItem>
          <EuiFlexItem grow={false}>
            <EuiSwitch
              checked={Boolean(value.log)}
              compressed
              disabled={disabled}
              label={<small>Log scale</small>}
              onChange={(e) => {
                const log = e.target.checked
                // A log range spaces its grid geometrically, so it uses a count.
                patch(log
                  ? { log, step: undefined, count: value.count ?? pointsPerRange }
                  : { log })
              }}
            />
          </EuiFlexItem>
        </EuiFlexGroup>
        {preview &&
          <EuiText color='subdued' size='xs' style={{ marginTop: '4px' }}>
            <small>Grid values: {preview}</small>
          </EuiText>
        }
      </>
    )
  }

  const renderSet = () => {
    const options = type === 'boolean'
      ? [{ label: 'true', value: true }, { label: 'false', value: false }]
      : (testable?.type === 'set'
        ? testable.values.map((v) => ({ label: formatValue(v) || String(v), value: v }))
        : [])
    const fixedOptions = options.length > 0
    const selected = (value.values || []).map((v) => ({ label: formatValue(v) || String(v), value: v }))
    return (
      <EuiComboBox
        aria-label='Values'
        compressed
        fullWidth
        isClearable
        isDisabled={disabled}
        noSuggestions={!fixedOptions}
        onChange={(opts) => onChange({ ...value, values: opts.map((o) => o.value) })}
        onCreateOption={fixedOptions ? undefined : (text) => {
          const parsed = parseValue(type, type === 'string' ? text : text.trim())
          if (parsed === undefined)
            return false
          if ((value.values || []).some((v) => v === parsed))
            return
          onChange({ ...value, values: [...(value.values || []), parsed] })
        }}
        options={options}
        placeholder={fixedOptions ? 'Choose values to test' : `Type a ${type} value and press Enter`}
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
          isDisabled={disabled}
          isFullWidth
          legend='Values to test'
          onChange={(id) => changeKind(id.replace(`${idPrefix}-`, ''))}
          options={kinds.map((k) => ({ id: `${idPrefix}-${k.id}`, label: k.label }))}
        />
      }
      {value?.type === 'range' && <div style={{ marginTop: '4px' }}>{renderRange()}</div>}
      {value?.type === 'set' && <div style={{ marginTop: '4px' }}>{renderSet()}</div>}
      {error &&
        <EuiText color='danger' size='xs' style={{ marginTop: '4px' }}>
          <small>{error}</small>
        </EuiText>
      }
    </div>
  )
}

export default ValuesToTestEditor
