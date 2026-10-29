/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  EuiBadge,
  EuiButtonGroup,
  EuiCallOut,
  EuiFieldNumber,
  EuiFieldText,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFormRow,
  EuiPanel,
  EuiSelect,
  EuiSpacer,
  EuiSwitch,
  EuiText,
} from '@elastic/eui'
import ValuesToTestEditor from './ValuesToTestEditor'
import { DEFAULT_POINTS_PER_RANGE, describeTestableValues } from '../hyperparameters'

const METRIC_LABELS = { mrr: 'MRR', ndcg: 'NDCG', precision: 'Precision', recall: 'Recall' }

/**
 * Controls for the hyperparameter optimization settings of a benchmark, or of
 * a test in the strategy editor.
 *
 * `form` is the form state from `defaultOptimizationForm`. `hyperparameters` is
 * the union of the hyperparameters of the candidate strategies. For each, the
 * benchmark tests all of the valid testable values by default. It can narrow
 * them, or stop testing the hyperparameter so that it keeps its promoted value.
 */
const OptimizationControls = ({
  form,
  setForm,
  hyperparameters = [],
  metrics = ['ndcg'],
  showHoldout = true,
  showValuesToTest = true,
  showSwitch = true,
  disabled = false,
  idPrefix = 'opt',
}) => {
  const patch = (fields) => setForm((prev) => ({ ...prev, ...fields }))
  const setEntry = (name, fields) => setForm((prev) => {
    const current = prev.values_to_test?.[name] || { enabled: true, values: undefined }
    return { ...prev, values_to_test: { ...prev.values_to_test, [name]: { ...current, ...fields } } }
  })

  // The values a benchmark starts testing when the user narrows a hyperparameter.
  // An open range starts as a finite window around the promoted value.
  const initialValues = (hp) => {
    const testable = hp.testable_values
    if (hp.type === 'boolean')
      return { type: 'set', values: [true, false] }
    if (testable?.type === 'set')
      return { type: 'set', values: [...testable.values] }
    const promoted = Number.isFinite(hp.promoted_value) ? hp.promoted_value : 0
    const span = Math.max(1, Math.abs(promoted))
    let min = testable?.min ?? promoted - span
    let max = testable?.max ?? promoted + span
    if (!(min < max))
      max = min + span
    return { type: 'range', min, max, log: false }
  }

  const renderValuesToTest = () => {
    if (!hyperparameters.length) {
      return (
        <EuiCallOut color='primary' iconType='iInCircle' size='s' title='No strategy defines hyperparameters'>
          <p>Without hyperparameters, each strategy runs as a single variant.</p>
        </EuiCallOut>
      )
    }
    return hyperparameters.map((hp) => {
      const entry = form.values_to_test?.[hp.name]
      const isTested = entry?.enabled !== false
      const isNarrowed = Boolean(entry?.values)
      const testable = hp.testable_values
      const isUnbounded = testable?.type === 'range' && (!Number.isFinite(testable.min) || !Number.isFinite(testable.max))
      return (
        <EuiPanel
          color='subdued'
          hasBorder={false}
          hasShadow={false}
          key={hp.name}
          paddingSize='s'
          style={{ marginBottom: '8px' }}
        >
          <EuiFlexGroup alignItems='center' gutterSize='s' responsive={false}>
            <EuiFlexItem grow>
              <EuiText size='s'>
                <b>{hp.name}</b>{' '}
                <EuiBadge color='hollow'><small>{hp.types.join(' / ')}</small></EuiBadge>
                <EuiBadge color='hollow'><small>{hp.strategies} {hp.strategies === 1 ? 'strategy' : 'strategies'}</small></EuiBadge>
              </EuiText>
              <EuiText color='subdued' size='xs'>
                <small>
                  {isTested
                    ? `Valid testable values: ${describeTestableValues(testable)}`
                    : `Keeps its promoted value, ${String(hp.promoted_value)}`}
                </small>
              </EuiText>
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiSwitch
                checked={isTested}
                compressed
                disabled={disabled}
                label={<small>Test</small>}
                onChange={(e) => setEntry(hp.name, { enabled: e.target.checked })}
              />
            </EuiFlexItem>
            {isTested &&
              <EuiFlexItem grow={false}>
                <EuiSwitch
                  checked={isNarrowed}
                  compressed
                  disabled={disabled || hp.hasTypeConflict}
                  label={<small>{hp.type === 'boolean' ? 'Choose values' : 'Narrow'}</small>}
                  onChange={(e) => setEntry(hp.name, { values: e.target.checked ? initialValues(hp) : undefined })}
                />
              </EuiFlexItem>
            }
          </EuiFlexGroup>
          {hp.hasTypeConflict &&
            <EuiText color='danger' size='xs'>
              <small>Strategies define this hyperparameter with different types, so its values can't be narrowed.</small>
            </EuiText>
          }
          {isTested && !isNarrowed && isUnbounded &&
            <EuiText color='danger' size='xs'>
              <small>The valid testable values are unbounded. Narrow them to a finite range, or turn off testing.</small>
            </EuiText>
          }
          {isTested && isNarrowed &&
            <>
              <EuiSpacer size='xs' />
              <ValuesToTestEditor
                disabled={disabled}
                idPrefix={`${idPrefix}-${hp.name}`}
                onChange={(values) => setEntry(hp.name, { values })}
                pointsPerRange={Number(form.points_per_range) || DEFAULT_POINTS_PER_RANGE}
                testable={testable}
                type={hp.type}
                value={entry.values}
              />
            </>
          }
        </EuiPanel>
      )
    })
  }

  return (
    <div>
      {showSwitch &&
        <EuiSwitch
          checked={form.enabled}
          disabled={disabled}
          label='Optimize hyperparameters'
          onChange={(e) => patch({ enabled: e.target.checked })}
        />
      }
      {form.enabled &&
        <>
          <EuiSpacer size='m' />

          {/* Algorithm */}
          <EuiFormRow display='rowCompressed' fullWidth label='Search'>
            <>
              <EuiButtonGroup
                buttonSize='compressed'
                idSelected={`${idPrefix}-algorithm-${form.algorithm}`}
                isDisabled={disabled}
                isFullWidth
                legend='Search algorithm'
                onChange={(id) => patch({ algorithm: id.replace(`${idPrefix}-algorithm-`, '') })}
                options={[
                  { id: `${idPrefix}-algorithm-grid`, label: 'Grid' },
                  { id: `${idPrefix}-algorithm-random`, label: 'Random' },
                ]}
              />
              <EuiSpacer size='xs' />
              <EuiFlexGroup gutterSize='xs' responsive={false}>
                {form.algorithm === 'grid' &&
                  <EuiFlexItem>
                    <EuiFieldNumber
                      aria-label='Points per range'
                      compressed
                      disabled={disabled}
                      min={2}
                      onChange={(e) => patch({ points_per_range: e.target.value })}
                      prepend={<small>Points per range</small>}
                      step={1}
                      value={form.points_per_range}
                    />
                  </EuiFlexItem>
                }
                {form.algorithm === 'random' &&
                  <EuiFlexItem>
                    <EuiFieldNumber
                      aria-label='Sample size'
                      compressed
                      disabled={disabled}
                      min={1}
                      onChange={(e) => patch({ sample_size: e.target.value })}
                      prepend={<small>Variants</small>}
                      step={1}
                      value={form.sample_size}
                    />
                  </EuiFlexItem>
                }
                <EuiFlexItem>
                  <EuiFieldText
                    aria-label='Seed'
                    compressed
                    disabled={disabled}
                    onChange={(e) => patch({ seed: e.target.value })}
                    placeholder='Benchmark ID'
                    prepend={<small>Seed</small>}
                    value={form.seed}
                  />
                </EuiFlexItem>
              </EuiFlexGroup>
            </>
          </EuiFormRow>
          <EuiSpacer size='m' />

          {/* Values to test */}
          {showValuesToTest &&
            <>
              <EuiFormRow
                display='rowCompressed'
                fullWidth
                helpText='Narrowing the values applies to every strategy that defines a hyperparameter with the same name. A range without a step or count gets the points per range as its grid.'
                label='Values to test'
              >
                <div>{renderValuesToTest()}</div>
              </EuiFormRow>
              <EuiSpacer size='m' />
            </>
          }

          {/* Objective */}
          <EuiFormRow
            display='rowCompressed'
            fullWidth
            helpText='The winner of each strategy is the variant with the best objective score.'
            label='Objective'
          >
            <EuiFlexGroup gutterSize='xs' responsive={false}>
              <EuiFlexItem>
                <EuiSelect
                  aria-label='Objective metric'
                  compressed
                  disabled={disabled}
                  onChange={(e) => patch({ objective_metric: e.target.value })}
                  options={metrics.map((m) => ({ value: m, text: METRIC_LABELS[m] || m }))}
                  value={form.objective_metric}
                />
              </EuiFlexItem>
              <EuiFlexItem>
                <EuiSelect
                  aria-label='Objective aggregation'
                  compressed
                  disabled={disabled}
                  onChange={(e) => patch({ objective_aggregation: e.target.value })}
                  options={[
                    { value: 'mean', text: 'Mean across scenarios' },
                    { value: 'median', text: 'Median across scenarios' },
                  ]}
                  value={form.objective_aggregation}
                />
              </EuiFlexItem>
            </EuiFlexGroup>
          </EuiFormRow>
          <EuiSpacer size='m' />

          {/* Latency constraint */}
          <EuiFormRow display='rowCompressed' fullWidth label='Latency constraint'>
            <>
              <EuiSwitch
                checked={form.latency_enabled}
                compressed
                disabled={disabled}
                label={<small>Exclude variants that are too slow from winning</small>}
                onChange={(e) => patch({ latency_enabled: e.target.checked })}
              />
              {form.latency_enabled &&
                <>
                  <EuiSpacer size='xs' />
                  <EuiFlexGroup gutterSize='xs' responsive={false}>
                    <EuiFlexItem grow={false} style={{ width: '120px' }}>
                      <EuiSelect
                        aria-label='Latency statistic'
                        compressed
                        disabled={disabled}
                        onChange={(e) => patch({ latency_stat: e.target.value })}
                        options={[
                          { value: 'mean', text: 'Mean' },
                          { value: 'median', text: 'Median' },
                          { value: 'p90', text: 'p90' },
                        ]}
                        value={form.latency_stat}
                      />
                    </EuiFlexItem>
                    <EuiFlexItem>
                      <EuiFieldNumber
                        aria-label='Maximum latency'
                        append={<small>ms</small>}
                        compressed
                        disabled={disabled}
                        isInvalid={!(Number(form.latency_max_ms) > 0)}
                        min={1}
                        onChange={(e) => patch({ latency_max_ms: e.target.value })}
                        prepend={<small>Max</small>}
                        value={form.latency_max_ms}
                      />
                    </EuiFlexItem>
                  </EuiFlexGroup>
                </>
              }
            </>
          </EuiFormRow>

          {/* Holdout */}
          {showHoldout &&
            <>
              <EuiSpacer size='m' />
              <EuiFormRow
                display='rowCompressed'
                fullWidth
                helpText='Scenarios the search never sees. Only the winner and the baseline variant run on them, so the holdout score is an unbiased estimate.'
                label='Holdout'
              >
                <EuiFlexGroup gutterSize='xs' responsive={false}>
                  <EuiFlexItem>
                    <EuiFieldNumber
                      aria-label='Holdout percent'
                      append={<small>%</small>}
                      compressed
                      disabled={disabled}
                      max={90}
                      min={0}
                      onChange={(e) => patch({ holdout_percent: e.target.value })}
                      prepend={<small>Reserve</small>}
                      step={1}
                      value={form.holdout_percent}
                    />
                  </EuiFlexItem>
                  <EuiFlexItem>
                    <EuiFieldText
                      aria-label='Holdout seed'
                      compressed
                      disabled={disabled}
                      onChange={(e) => patch({ holdout_seed: e.target.value })}
                      placeholder='Search seed'
                      prepend={<small>Seed</small>}
                      value={form.holdout_seed}
                    />
                  </EuiFlexItem>
                </EuiFlexGroup>
              </EuiFormRow>
              {!(Number(form.holdout_percent) > 0) &&
                <EuiText color='warning' size='xs' style={{ marginTop: '4px' }}>
                  <small>Without a holdout, the scores of the winner are in-sample and optimistic.</small>
                </EuiText>
              }
            </>
          }
        </>
      }
    </div>
  )
}

export default OptimizationControls
