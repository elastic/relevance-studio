/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useState } from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { EuiProvider } from '@elastic/eui'
import HyperparameterEditor from '../Layout/HyperparameterEditor'
import OptimizationControls from '../Layout/OptimizationControls'
import VariantsTable, { sortVariants } from '../Layout/VariantsTable'
import { buildVariantOverride } from '../Pages/RunsView/ChartMetricsHeatmap'
import { optimizedStrategies, sensitivitySeries } from '../Pages/RunsView/ChartSensitivity'
import hp from '../hyperparameters'

const SOURCE = '{"boost":{{hp.boost}},"q":"{{text}}","f":"{{hp.field}}"}'

const withProvider = (ui) => render(<EuiProvider>{ui}</EuiProvider>)

const variant = (id, rank, values, ndcg, extra = {}) => ({
  variant_id: id,
  rank,
  values,
  is_baseline: false,
  is_winner: rank === 1,
  is_run_winner: rank === 1,
  violates_constraint: false,
  aggregates: {
    tuning: { metrics: { ndcg: { avg: ndcg, median: ndcg } }, took: { median: 10 * rank }, coverage: 0.9 },
  },
  ...extra,
})

describe('HyperparameterEditor', () => {
  const Harness = ({ initial = [], source = SOURCE }) => {
    const [definitions, setDefinitions] = useState(initial)
    const validation = hp.validateDefinitions(definitions, source)
    return (
      <>
        <HyperparameterEditor
          definitions={definitions}
          onChange={setDefinitions}
          source={source}
          validation={validation}
        />
        <pre data-testid='state'>{JSON.stringify(definitions)}</pre>
      </>
    )
  }

  it('offers to define each undefined reference', () => {
    withProvider(<Harness />)
    expect(screen.getByText('hp.boost')).toBeInTheDocument()
    expect(screen.getByText('hp.field')).toBeInTheDocument()
  })

  it('adds a definition named after a reference', () => {
    withProvider(<Harness />)
    fireEvent.click(screen.getByText('hp.boost').closest('button'))
    const state = JSON.parse(screen.getByTestId('state').textContent)
    expect(state).toEqual([{ name: 'boost', type: 'number', promoted_value: 0, testable_values: { type: 'range' } }])
  })

  it('reports an error for an undefined reference and a warning for an unused definition', () => {
    withProvider(<Harness initial={[{ name: 'unused', type: 'number', promoted_value: 1, testable_values: { type: 'range' } }]} />)
    expect(screen.getByText(/'\{\{hp\.boost\}\}', which isn't defined/)).toBeInTheDocument()
    expect(screen.getByText(/'unused' isn't used in the template/)).toBeInTheDocument()
  })

  it('uses a dropdown with true and false for a boolean promoted value', () => {
    withProvider(<Harness initial={[{ name: 'flag', type: 'boolean', promoted_value: true }]} source='' />)
    const select = screen.getByLabelText('Promoted value')
    expect(select.tagName).toBe('SELECT')
    expect(Array.from(select.options).map((o) => o.value)).toEqual(['true', 'false'])
    fireEvent.change(select, { target: { value: 'false' } })
    expect(JSON.parse(screen.getByTestId('state').textContent)[0].promoted_value).toBe(false)
  })

  it('removes a definition', () => {
    withProvider(<Harness initial={[{ name: 'boost', type: 'number', promoted_value: 1, testable_values: { type: 'range' } }]} source='' />)
    fireEvent.click(screen.getByLabelText('Remove hyperparameter'))
    expect(JSON.parse(screen.getByTestId('state').textContent)).toEqual([])
  })
})

describe('OptimizationControls', () => {
  const pool = hp.hyperparametersOfPool([{
    hyperparameters: [{
      name: 'boost', type: 'number', promoted_value: 2,
      testable_values: { type: 'range', min: 0, max: 4 },
    }],
  }])

  const Harness = ({ enabled = true }) => {
    const [form, setForm] = useState({ ...hp.defaultOptimizationForm(), enabled })
    return (
      <>
        <OptimizationControls form={form} hyperparameters={pool} metrics={['ndcg', 'mrr']} setForm={setForm} />
        <pre data-testid='form'>{JSON.stringify(form)}</pre>
      </>
    )
  }

  it('hides the settings until optimization is enabled', () => {
    withProvider(<Harness enabled={false} />)
    expect(screen.queryByText('Objective')).not.toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Optimize hyperparameters'))
    expect(screen.getByText('Objective')).toBeInTheDocument()
  })

  it('lists the pooled hyperparameters with their valid testable values', () => {
    withProvider(<Harness />)
    expect(screen.getByText('boost')).toBeInTheDocument()
    expect(screen.getByText('Valid testable values: 0 to 4')).toBeInTheDocument()
  })

  it('narrows the values starting from the valid testable values', () => {
    withProvider(<Harness />)
    fireEvent.click(screen.getByLabelText('Narrow'))
    const form = JSON.parse(screen.getByTestId('form').textContent)
    expect(form.values_to_test.boost.values).toEqual({ type: 'range', min: 0, max: 4, log: false })
  })

  it('turns off testing so the hyperparameter keeps its promoted value', () => {
    withProvider(<Harness />)
    fireEvent.click(screen.getByLabelText('Test'))
    const form = JSON.parse(screen.getByTestId('form').textContent)
    expect(form.values_to_test.boost.enabled).toBe(false)
    expect(screen.getByText('Keeps its promoted value, 2')).toBeInTheDocument()
  })

  it('shows the points per range for a grid search', () => {
    withProvider(<Harness />)
    expect(screen.getByLabelText('Points per range')).toBeInTheDocument()
  })

  it('warns when there is no holdout', () => {
    withProvider(<Harness />)
    fireEvent.change(screen.getByLabelText('Holdout percent'), { target: { value: '0' } })
    expect(screen.getByText(/in-sample and optimistic/)).toBeInTheDocument()
  })
})

describe('VariantsTable', () => {
  const items = [
    variant('aaaaaaaa11', 1, { boost: 3 }, 0.8),
    variant('bbbbbbbb22', 2, { boost: 1 }, 0.7, { is_baseline: true, is_winner: false, is_run_winner: false }),
    variant('cccccccc33', 3, { boost: 2 }, 0.6, { is_winner: false, is_run_winner: false, violates_constraint: true }),
  ]
  const definitions = [{ name: 'boost', type: 'number', promoted_value: 1, testable_values: { type: 'range' } }]

  it('shows a column per hyperparameter and flags the winner, baseline and slow variants', () => {
    withProvider(<VariantsTable hyperparameters={definitions} items={items} metrics={['ndcg']} />)
    expect(screen.getByText('boost')).toBeInTheDocument()
    expect(screen.getByText('Winner')).toBeInTheDocument()
    expect(screen.getByText('Baseline')).toBeInTheDocument()
    expect(screen.getByText('Slow')).toBeInTheDocument()
    expect(screen.getByText('aaaaaaaa')).toBeInTheDocument()
  })

  it('labels the run winner when ranking exploratively', () => {
    withProvider(<VariantsTable exploratory hyperparameters={definitions} items={items} metrics={['ndcg']} />)
    expect(screen.getByText('Run winner')).toBeInTheDocument()
    expect(screen.queryByText('Winner')).not.toBeInTheDocument()
  })

  it('selects a variant from its link', () => {
    const onSelect = jest.fn()
    withProvider(<VariantsTable hyperparameters={definitions} items={items} metrics={['ndcg']} onSelect={onSelect} />)
    fireEvent.click(screen.getByText('bbbbbbbb'))
    expect(onSelect).toHaveBeenCalledWith(items[1])
  })

  it('shows the holdout column only when a variant has holdout scores', () => {
    const { rerender } = withProvider(<VariantsTable hyperparameters={definitions} items={items} metrics={['ndcg']} />)
    expect(screen.queryByText('Holdout NDCG')).not.toBeInTheDocument()
    const withHoldout = [
      { ...items[0], aggregates: { ...items[0].aggregates, holdout: { metrics: { ndcg: { avg: 0.75 } } } } },
      ...items.slice(1),
    ]
    rerender(<EuiProvider><VariantsTable hyperparameters={definitions} items={withHoldout} metrics={['ndcg']} /></EuiProvider>)
    expect(screen.getByText('Holdout NDCG')).toBeInTheDocument()
    expect(screen.getByText('0.7500')).toBeInTheDocument()
  })

  it('sorts locally by hyperparameter and metric', () => {
    expect(sortVariants(items, 'hp:boost', false).map((v) => v.variant_id)).toEqual(['bbbbbbbb22', 'cccccccc33', 'aaaaaaaa11'])
    expect(sortVariants(items, 'metric:ndcg', true).map((v) => v.rank)).toEqual([1, 2, 3])
    expect(sortVariants(items, 'took', true).map((v) => v.rank)).toEqual([3, 2, 1])
  })

  it('sorts variants without a value last', () => {
    const missing = [variant('x', 1, {}, 0.5), { ...variant('y', 2, { boost: 1 }, 0.4) }]
    expect(sortVariants(missing, 'hp:boost', false).map((v) => v.variant_id)).toEqual(['y', 'x'])
  })
})

describe('sensitivity chart data', () => {
  it('plots numeric hyperparameters on a numeric axis', () => {
    const series = sensitivitySeries({ kind: 'numeric', points: [[0, 0.4], [2, 0.6], [4, 0.5]] })
    expect(series.kind).toBe('numeric')
    expect(series.data).toEqual([{ x: 0, y: 0.4 }, { x: 2, y: 0.6 }, { x: 4, y: 0.5 }])
    expect(series.min).toBe(0.4)
    expect(series.max).toBe(0.6)
  })

  it('plots other hyperparameters as categories', () => {
    const series = sensitivitySeries({ kind: 'categorical', points: [['name.text', 0.5], [true, 0.6]] })
    expect(series.kind).toBe('categorical')
    expect(series.data.map((d) => d.x)).toEqual(['name.text', 'true'])
  })

  it('handles an entry without points', () => {
    expect(sensitivitySeries({ kind: 'numeric', points: [] }).data).toEqual([])
    expect(sensitivitySeries(undefined).data).toEqual([])
  })

  it('keeps only strategies that ran more than one variant', () => {
    const summary = { strategies: [{ strategy_id: 'a', variant_count: 1 }, { strategy_id: 'b', variant_count: 9 }] }
    expect(optimizedStrategies(summary).map((s) => s.strategy_id)).toEqual(['b'])
    expect(optimizedStrategies(null)).toEqual([])
  })
})

describe('buildVariantOverride', () => {
  it('averages the metrics of a variant across scenarios', () => {
    const override = buildVariantOverride('s1', 'v1', [
      { scenario_id: 'a', metrics: { ndcg: 0.2, mrr: 1 } },
      { scenario_id: 'b', metrics: { ndcg: 0.6, mrr: 0 } },
    ])
    expect(override.strategyId).toBe('s1')
    expect(override.variantId).toBe('v1')
    expect(override.avg.ndcg).toBeCloseTo(0.4)
    expect(override.avg.mrr).toBeCloseTo(0.5)
    expect(override.byScenario.a).toEqual({ ndcg: 0.2, mrr: 1 })
  })

  it('skips missing values', () => {
    const override = buildVariantOverride('s1', 'v1', [
      { scenario_id: 'a', metrics: { ndcg: null } },
      { scenario_id: 'b', metrics: { ndcg: 0.5 } },
    ])
    expect(override.avg.ndcg).toBe(0.5)
  })
})
