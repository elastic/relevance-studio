/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import eb from '../editorBenchmark'

const boost = { name: 'boost', type: 'number', promoted_value: 1, testable_values: { type: 'range', min: 0, max: 5 } }
const fuzzy = { name: 'fuzzy', type: 'boolean', promoted_value: true }
const saved = { name: 'S', tags: ['t'], source: '{"q":"{{text}}","b":{{hp.boost}}}', hyperparameters: [boost] }
const draft = { name: 'S', tags: ['t'], source: '{"q":"{{text}}","b":{{hp.boost}},"f":{{hp.fuzzy}}}', hyperparameters: [boost, fuzzy] }

describe('buildEditorTask', () => {
  test('compares the saved strategy and the draft', () => {
    const task = eb.buildEditorTask({ strategyId: 's1', saved, draft, form: eb.defaultEditorForm(), compare: true })
    expect(task.strategies.docs.map((d) => d._id)).toEqual(['s1', 's1_draft'])
    expect(task.strategies.docs[0]._source.params).toEqual(['text'])
    expect(task.strategies.docs[1]._source.hyperparameters).toHaveLength(2)
    expect(task.metrics).toEqual(['ndcg', 'precision', 'recall'])
    expect(task.k).toBe(10)
    expect(task.scenarios).toEqual({})
    expect(task.optimization).toBeUndefined()
  })

  test('runs only the draft without a comparison', () => {
    const task = eb.buildEditorTask({ strategyId: 's1', saved, draft, form: eb.defaultEditorForm(), compare: false })
    expect(task.strategies.docs.map((d) => d._id)).toEqual(['s1'])
  })

  test('keeps the saved strategy at its promoted values when testing hyperparameters', () => {
    const form = eb.defaultEditorForm()
    form.optimization.enabled = true
    form.scenario_tags = ['news']
    const task = eb.buildEditorTask({ strategyId: 's1', saved, draft, form, compare: true })
    expect(task.scenarios.tags).toEqual(['news'])
    expect(task.optimization.holdout.ratio).toBe(0.2)
    expect(task.optimization.values_to_test).toEqual([{ name: 'boost', strategy_id: 's1', enabled: false }])
  })

  test("doesn't test hyperparameters when the draft has none", () => {
    const form = eb.defaultEditorForm()
    form.optimization.enabled = true
    const task = eb.buildEditorTask({ strategyId: 's1', saved, draft: { ...draft, hyperparameters: [] }, form, compare: true })
    expect(task.optimization).toBeUndefined()
  })
})

describe('validateEditorForm', () => {
  test('needs metrics, k and an objective among the metrics', () => {
    const form = eb.defaultEditorForm()
    expect(eb.validateEditorForm(form, draft)).toEqual([])
    form.optimization.enabled = true
    form.metrics = ['precision']
    expect(eb.validateEditorForm(form, draft)).toHaveLength(1)
    form.metrics = []
    form.k = 0
    expect(eb.validateEditorForm(form, draft)).toHaveLength(3)
  })
})

const metrics = (ndcg) => ({ metrics: { ndcg: { avg: ndcg } } })
const run = {
  task: { optimization: { holdout: { ratio: 0.2 } } },
  summary: {
    strategy_id: {
      s1: { _total: metrics(0.5), by_scenario_id: { a: metrics(0.9), b: metrics(0.2), c: metrics(0.4) } },
      s1_draft: {
        _total: metrics(0.6),
        optimization: { score_basis: 'holdout' },
        by_scenario_id: { a: metrics(0.7), b: metrics(0.5), c: metrics(0.4) },
      },
    },
  },
  runtime: {
    scenarios: {
      a: { name: 'Alpha', _split: 'tuning' },
      b: { name: 'Bravo', _split: 'tuning' },
      c: { name: 'Charlie', _split: 'holdout' },
    },
  },
  variants: [
    { strategy_id: 's1_draft', variant_id: 'v2', rank: 2 },
    { strategy_id: 's1', variant_id: 'v0', rank: 1 },
    { strategy_id: 's1_draft', variant_id: 'v1', rank: 1 },
  ],
}

describe('comparisons', () => {
  test('compare the headline scores', () => {
    const [row] = eb.compareStrategies(run, 's1', 's1_draft', ['ndcg'])
    expect(row.saved).toBe(0.5)
    expect(row.draft).toBe(0.6)
    expect(row.delta).toBeCloseTo(0.1)
    expect(eb.compareStrategies(run, null, 's1_draft', ['ndcg'])[0].delta).toBeNull()
  })

  test('order scenarios by the biggest regression first', () => {
    const rows = eb.compareScenarios(run, 's1', 's1_draft', 'ndcg')
    expect(rows.map((r) => r.name)).toEqual(['Alpha', 'Charlie', 'Bravo'])
    expect(rows[0].delta).toBeCloseTo(-0.2)
    expect(rows[1].split).toBe('holdout')
  })

  test('order scenarios by the weakest draft score without a comparison', () => {
    const rows = eb.compareScenarios(run, null, 's1_draft', 'ndcg')
    expect(rows.map((r) => r.name)).toEqual(['Charlie', 'Bravo', 'Alpha'])
  })

  test('report the basis, scenario counts and draft variants', () => {
    expect(eb.scoreBasis(run, 's1_draft')).toBe('holdout')
    expect(eb.scoreBasis({ summary: run.summary }, 's1_draft')).toBe('all')
    expect(eb.scenarioCounts(run)).toEqual({ tuning: 2, holdout: 1, total: 3 })
    expect(eb.draftVariants(run, 's1_draft').map((v) => v.variant_id)).toEqual(['v1', 'v2'])
  })
})

describe('staleKey', () => {
  test('changes with the draft, the saved strategy and the form', () => {
    const form = eb.defaultEditorForm()
    const key = eb.staleKey({ saved, draft, form })
    expect(eb.staleKey({ saved, draft, form: eb.defaultEditorForm() })).toBe(key)
    expect(eb.staleKey({ saved, draft: { ...draft, source: '{}' }, form })).not.toBe(key)
    expect(eb.staleKey({ saved: { ...saved, hyperparameters: [] }, draft, form })).not.toBe(key)
    expect(eb.staleKey({ saved, draft, form: { ...form, k: 5 } })).not.toBe(key)
  })
})

describe('compareWinnerToBaseline', () => {
  test('compare the best variant to the promoted values on the holdout', () => {
    const r = {
      summary: {
        strategy_id: {
          s1: {
            optimization: {
              score_basis: 'holdout',
              holdout: metrics(0.6), baseline_holdout: metrics(0.5),
              tuning: metrics(0.9), baseline_tuning: metrics(0.1),
            },
          },
        },
      },
    }
    const [row] = eb.compareWinnerToBaseline(r, 's1', ['ndcg'])
    expect(row.draft).toBe(0.6)
    expect(row.saved).toBe(0.5)
    expect(row.delta).toBeCloseTo(0.1)
  })
})
