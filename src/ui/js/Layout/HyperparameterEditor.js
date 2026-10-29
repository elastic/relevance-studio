/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  EuiButton,
  EuiButtonEmpty,
  EuiButtonIcon,
  EuiCallOut,
  EuiCode,
  EuiFieldNumber,
  EuiFieldText,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFormRow,
  EuiPanel,
  EuiSelect,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import TestableValuesEditor from './TestableValuesEditor'
import {
  HYPERPARAMETER_TYPES,
  checkValueType,
  extractRefs,
} from '../hyperparameters'

const defaultFor = (type) => {
  if (type === 'number') return 0
  if (type === 'boolean') return false
  return ''
}

// The valid testable values a new hyperparameter of a type starts with.
// A range starts unbounded, a set starts empty, and a boolean has none.
const testableFor = (type) => {
  if (type === 'number') return { type: 'range' }
  if (type === 'string') return { type: 'set', values: [] }
  return undefined
}

/**
 * Edit the hyperparameter definitions of a strategy: name, type, promoted
 * value, and valid testable values.
 *
 * `validation` is `{ errors, warnings }` from `validateDefinitions`.
 */
const HyperparameterEditor = ({
  definitions,
  onChange,
  source = '',
  validation = { errors: [], warnings: [] },
}) => {
  const undefinedRefs = extractRefs(source).filter(
    (name) => !definitions.some((hp) => hp.name === name)
  )

  const update = (index, fields) => {
    onChange(definitions.map((hp, i) => i === index ? { ...hp, ...fields } : hp))
  }

  const add = (name = '') => {
    onChange([...definitions, { name, type: 'number', promoted_value: 0, testable_values: testableFor('number') }])
  }

  const remove = (index) => {
    onChange(definitions.filter((_, i) => i !== index))
  }

  const changeType = (index, type) => {
    const hp = definitions[index]
    // Keep the promoted value and testable values when they still fit the new type
    const keepValue = checkValueType(type, hp.promoted_value)
    const testable = hp.testable_values
    const keepTestable = testable && (
      (testable.type === 'range' && type === 'number')
      || (testable.type === 'set' && testable.values.every((v) => checkValueType(type, v)))
    )
    update(index, {
      type,
      promoted_value: keepValue ? hp.promoted_value : defaultFor(type),
      testable_values: type === 'boolean' ? undefined : (keepTestable ? testable : testableFor(type)),
    })
  }

  const renderPromotedValue = (hp, index) => {
    if (hp.type === 'boolean') {
      return (
        <EuiSelect
          aria-label='Promoted value'
          compressed
          onChange={(e) => update(index, { promoted_value: e.target.value === 'true' })}
          options={[{ value: 'true', text: 'true' }, { value: 'false', text: 'false' }]}
          value={String(hp.promoted_value === true)}
        />
      )
    }
    if (hp.type === 'string') {
      return (
        <EuiFieldText
          aria-label='Promoted value'
          compressed
          isInvalid={!checkValueType('string', hp.promoted_value)}
          onChange={(e) => update(index, { promoted_value: e.target.value })}
          value={hp.promoted_value ?? ''}
        />
      )
    }
    return (
      <EuiFieldNumber
        aria-label='Promoted value'
        compressed
        isInvalid={!checkValueType('number', hp.promoted_value)}
        onChange={(e) => {
          const text = e.target.value
          update(index, { promoted_value: text === '' ? undefined : Number(text) })
        }}
        step='any'
        value={hp.promoted_value ?? ''}
      />
    )
  }

  const renderDefinition = (hp, index) => (
    <EuiPanel
      color='subdued'
      hasBorder={false}
      hasShadow={false}
      key={index}
      paddingSize='s'
      style={{ marginBottom: '8px' }}
    >
      <EuiFlexGroup alignItems='flexEnd' gutterSize='s' responsive={false}>
        <EuiFlexItem grow={3}>
          <EuiFormRow display='rowCompressed' label='Name'>
            <EuiFieldText
              aria-label='Name'
              compressed
              isInvalid={hp.name !== '' && !/^\w+$/.test(hp.name)}
              onChange={(e) => update(index, { name: e.target.value.trim() })}
              placeholder='name'
              prepend={<small>hp.</small>}
              value={hp.name}
            />
          </EuiFormRow>
        </EuiFlexItem>
        <EuiFlexItem grow={2}>
          <EuiFormRow display='rowCompressed' label='Type'>
            <EuiSelect
              aria-label='Type'
              compressed
              onChange={(e) => changeType(index, e.target.value)}
              options={HYPERPARAMETER_TYPES.map((t) => ({ value: t, text: t }))}
              value={hp.type}
            />
          </EuiFormRow>
        </EuiFlexItem>
        <EuiFlexItem grow={2}>
          <EuiFormRow display='rowCompressed' label='Promoted value'>
            {renderPromotedValue(hp, index)}
          </EuiFormRow>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiButtonIcon
            aria-label='Remove hyperparameter'
            color='danger'
            iconType='trash'
            onClick={() => remove(index)}
          />
        </EuiFlexItem>
      </EuiFlexGroup>
      {hp.type !== 'boolean' &&
        <>
          <EuiSpacer size='xs' />
          <EuiFormRow display='rowCompressed' fullWidth label='Valid testable values'>
            <TestableValuesEditor
              idPrefix={`hp-${index}`}
              onChange={(testable) => update(index, { testable_values: testable })}
              type={hp.type}
              value={hp.testable_values}
            />
          </EuiFormRow>
        </>
      }
    </EuiPanel>
  )

  return (
    <div>
      {definitions.length === 0 &&
        <EuiText color='subdued' size='xs'>
          <p>
            Define a hyperparameter, then reference it in the template as <EuiCode>{'{{hp.name}}'}</EuiCode>.
            Its valid testable values are the values a benchmark may test to find the best promoted value.
          </p>
        </EuiText>
      }
      {definitions.map(renderDefinition)}
      <EuiFlexGroup gutterSize='s' responsive={false} wrap>
        <EuiFlexItem grow={false}>
          <EuiButton iconType='plusInCircle' onClick={() => add()} size='s'>
            Add hyperparameter
          </EuiButton>
        </EuiFlexItem>
        {undefinedRefs.map((name) => (
          <EuiFlexItem grow={false} key={name}>
            <EuiButtonEmpty iconType='plusInCircle' onClick={() => add(name)} size='s'>
              Define <EuiCode transparentBackground>{`hp.${name}`}</EuiCode>
            </EuiButtonEmpty>
          </EuiFlexItem>
        ))}
      </EuiFlexGroup>
      {validation.errors.length > 0 &&
        <>
          <EuiSpacer size='s' />
          <EuiCallOut color='danger' iconType='warning' size='s' title='Fix before saving'>
            <ul style={{ margin: 0, paddingLeft: '16px' }}>
              {validation.errors.map((message) => <li key={message}><small>{message}</small></li>)}
            </ul>
          </EuiCallOut>
        </>
      }
      {validation.warnings.length > 0 &&
        <>
          <EuiSpacer size='s' />
          <EuiCallOut color='warning' iconType='help' size='s' title='Check'>
            <ul style={{ margin: 0, paddingLeft: '16px' }}>
              {validation.warnings.map((message) => <li key={message}><small>{message}</small></li>)}
            </ul>
          </EuiCallOut>
        </>
      }
    </div>
  )
}

export default HyperparameterEditor
