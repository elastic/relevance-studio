/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import hp from '../hyperparameters'
import utils from '../utils'

const SOURCE = '{"query":{"match":{"{{hp.field}}":{"query":"{{text}}","boost":{{hp.boost}}}}}}'

const BOOST = {
  name: 'boost', type: 'number', promoted_value: 2,
  testable_values: { type: 'range', min: 0, max: 4 },
}
const FIELD = {
  name: 'field', type: 'string', promoted_value: 'name.text',
  testable_values: { type: 'set', values: ['name.text', 'name.ngram'] },
}
// Grid search over the boost range in steps of 1: 0, 1, 2, 3, 4
const STEP_1 = [{ name: 'boost', values: { type: 'range', min: 0, max: 4, step: 1 } }]
const resolve = (definitions, entries = [], optimize = true, points = 5) =>
  hp.resolveHyperparameters(definitions, entries, 's1', points, optimize)

describe('template references', () => {
  it('extracts hyperparameter references, including toJson sections', () => {
    expect(hp.extractRefs(SOURCE)).toEqual(['boost', 'field'])
    expect(hp.extractRefs('{"a":{{#toJson}}hp.size{{/toJson}},"b":"{{ hp.x }}"}')).toEqual(['size', 'x'])
  })

  it('excludes hyperparameters from the scenario params', () => {
    expect(hp.extractScenarioParams(SOURCE)).toEqual(['text'])
  })

  it('renders only the hp tags and keeps scenario variables', () => {
    const out = hp.renderHyperparameters(SOURCE, { boost: 2.5, field: 'name.text' })
    expect(out).toBe('{"query":{"match":{"name.text":{"query":"{{text}}","boost":2.5}}}}')
  })

  it('renders toJson sections as JSON', () => {
    expect(hp.renderHyperparameters('{"a":{{#toJson}}hp.flag{{/toJson}}}', { flag: true })).toBe('{"a":true}')
  })

  it('throws when a referenced hyperparameter has no value', () => {
    expect(() => hp.renderHyperparameters(SOURCE, { boost: 1 })).toThrow(/field/)
  })

  it('applies hyperparameter values before scenario values', () => {
    const query = hp.applyTemplate(SOURCE, { text: 'shoes' }, { boost: 3, field: 'name.ngram' })
    expect(query).toEqual({ query: { match: { 'name.ngram': { query: 'shoes', boost: 3 } } } })
  })
})

describe('formatJsonWithMustache', () => {
  it('keeps distinct variables distinct', () => {
    const formatted = utils.formatJsonWithMustache(SOURCE)
    expect(formatted).toContain('"{{ hp.field }}"')
    expect(formatted).toContain('"query": "{{ text }}"')
    expect(formatted).toContain('"boost": {{ hp.boost }}')
  })

  it('round-trips toJson sections', () => {
    const formatted = utils.formatJsonWithMustache('{"size":{{#toJson}}hp.size{{/toJson}},"q":"{{text}}"}')
    expect(formatted).toContain('"size": {{#toJson}}hp.size{{/toJson}}')
    expect(formatted).toContain('"q": "{{ text }}"')
  })

  it('still rejects invalid JSON', () => {
    expect(() => utils.formatJsonWithMustache('{"a":')).toThrow(/validation failed/)
  })
})

describe('validateDefinitions', () => {
  it('accepts matching definitions', () => {
    const { errors, warnings } = hp.validateDefinitions([BOOST, FIELD], SOURCE)
    expect(errors).toEqual([])
    expect(warnings).toEqual([])
  })

  it('errors on an undefined reference', () => {
    const { errors } = hp.validateDefinitions([BOOST], SOURCE)
    expect(errors).toEqual([expect.stringContaining("'{{hp.field}}'")])
  })

  it('warns on an unused definition', () => {
    const unused = { name: 'unused', type: 'number', promoted_value: 1, testable_values: { type: 'range' } }
    const { errors, warnings } = hp.validateDefinitions([BOOST, FIELD, unused], SOURCE)
    expect(errors).toEqual([])
    expect(warnings).toEqual([expect.stringContaining("'unused'")])
  })

  it('errors on invalid names, duplicate names and mismatched promoted values', () => {
    const range = { type: 'range' }
    const { errors } = hp.validateDefinitions([
      { name: 'bad name', type: 'number', promoted_value: 1, testable_values: range },
      { name: 'dup', type: 'number', promoted_value: 1, testable_values: range },
      { name: 'dup', type: 'number', promoted_value: 1, testable_values: range },
      { name: 'count', type: 'number', promoted_value: 'x', testable_values: range },
    ], '')
    expect(errors.some((e) => e.includes('bad name'))).toBe(true)
    expect(errors.some((e) => e.includes("'dup' is defined more than once"))).toBe(true)
    expect(errors.some((e) => e.includes("promoted value of 'count'"))).toBe(true)
  })

  it('rejects ranges on non-numbers, missing testable values and unsafe strings', () => {
    const { errors } = hp.validateDefinitions([
      { name: 'label', type: 'string', promoted_value: 'a', testable_values: { type: 'range', min: 0 } },
      { name: 'text', type: 'string', promoted_value: 'say "hi"', testable_values: { type: 'set', values: ['a', 'b'] } },
      { name: 'missing', type: 'number', promoted_value: 1 },
    ], '')
    expect(errors.some((e) => e.includes('needs the number type'))).toBe(true)
    expect(errors.some((e) => e.includes('quotes'))).toBe(true)
    expect(errors.some((e) => e.includes('Valid testable values of \'missing\': Valid testable values are required'))).toBe(true)
  })

  it('requires the promoted value to be one of the testable values', () => {
    const outside = hp.validateDefinitions([{ ...BOOST, promoted_value: 9 }], '').errors
    expect(outside).toEqual([expect.stringContaining('must be one of its valid testable values')])
    const notInSet = hp.validateDefinitions([{ ...FIELD, promoted_value: 'other' }], '').errors
    expect(notInSet).toEqual([expect.stringContaining('must be one of its valid testable values')])
  })

  it('gives a boolean the testable values true and false', () => {
    const flag = { name: 'flag', type: 'boolean', promoted_value: true }
    expect(hp.validateDefinitions([flag], '').errors).toEqual([])
    expect(hp.definitionsForSave([flag])).toEqual([{ name: 'flag', type: 'boolean', promoted_value: true }])
  })
})

describe('validateTestableValues', () => {
  const validate = (type, testable) => hp.validateTestableValues(type, testable)

  it('allows either bound of a range to be open', () => {
    expect(validate('number', { type: 'range' })).toBeNull()
    expect(validate('number', { type: 'range', min: 0 })).toBeNull()
    expect(validate('number', { type: 'range', max: 10 })).toBeNull()
    expect(validate('number', { type: 'range', min: 0, max: 10 })).toBeNull()
  })

  it('needs the minimum below the maximum', () => {
    expect(validate('number', { type: 'range', min: 5, max: 5 })).toMatch(/less than/)
    expect(validate('number', { type: 'range', min: 6, max: 5 })).toMatch(/less than/)
  })

  it('needs a set of at least two distinct values of the type', () => {
    expect(validate('string', { type: 'set', values: ['a'] })).toMatch(/at least two/)
    expect(validate('number', { type: 'set', values: [1, 1] })).toMatch(/at least two/)
    expect(validate('number', { type: 'set', values: [1, 'a'] })).toMatch(/not a valid number/)
    expect(validate('number', { type: 'set', values: [1, 2] })).toBeNull()
  })

  it('has nothing to validate for a boolean', () => {
    expect(validate('boolean', undefined)).toBeNull()
  })
})

describe('validateValuesToTest', () => {
  const testable = { type: 'range', min: 0 }
  const range = (extra) => hp.validateValuesToTest('number', testable, { type: 'range', min: 1, max: 10, ...extra })

  it('validates range rules', () => {
    expect(range({ step: 1 })).toBeNull()
    expect(range({ count: 3 })).toBeNull()
    expect(range({ step: 1, count: 3 })).toMatch(/either step or count/)
    expect(range({ log: true, step: 1 })).toMatch(/count instead of step/)
    expect(range({ min: 0, log: true, count: 3 })).toMatch(/above 0/)
    expect(range({ min: 11 })).toMatch(/less than the maximum/)
    expect(range({ count: 1 })).toMatch(/at least 2/)
  })

  it('needs a finite range', () => {
    expect(hp.validateValuesToTest('number', testable, { type: 'range', min: 1 })).toMatch(/minimum and a maximum/)
  })

  it('keeps the values within the valid testable values', () => {
    expect(hp.validateValuesToTest('number', testable, { type: 'range', min: -1, max: 5 })).toMatch(/below the valid testable minimum/)
    expect(hp.validateValuesToTest('number', { type: 'range', max: 5 }, { type: 'range', min: 1, max: 6 })).toMatch(/above the valid testable maximum/)
    expect(hp.validateValuesToTest('string', FIELD.testable_values, { type: 'set', values: ['name.text', 'x'] })).toMatch(/not one of/)
    expect(hp.validateValuesToTest('string', FIELD.testable_values, { type: 'set', values: ['name.text', 'name.ngram'] })).toBeNull()
  })

  it("doesn't allow a range over a set of testable values", () => {
    const numbers = { type: 'set', values: [1, 2, 3] }
    expect(hp.validateValuesToTest('number', numbers, { type: 'range', min: 1, max: 2 })).toMatch(/set/)
  })
})

describe('variant counts', () => {
  it('counts a grid as the product of the value counts', () => {
    expect(hp.countVariants(resolve([BOOST, FIELD], STEP_1), 'grid')).toBe(5 * 2)
  })

  it('adds the baseline when the promoted value is off the grid', () => {
    const off = { ...BOOST, promoted_value: 2.5 }
    expect(hp.countVariants(resolve([off], STEP_1), 'grid')).toBe(6)
  })

  it('spaces log ranges geometrically with a count', () => {
    const lr = { name: 'lr', type: 'number', promoted_value: 0.01, testable_values: { type: 'range', min: 0 } }
    const entries = [{ name: 'lr', values: { type: 'range', min: 0.001, max: 0.1, count: 3, log: true } }]
    const [resolved] = resolve([lr], entries)
    expect(hp.gridValues(resolved)).toEqual([0.001, 0.01, 0.1])
    expect(hp.countVariants([resolved], 'grid')).toBe(3)
  })

  it('uses the points per range for a range without a step or count', () => {
    const [five] = resolve([BOOST])
    expect(five.values_to_test.count).toBe(5)
    expect(hp.gridValues(five)).toEqual([0, 1, 2, 3, 4])
    const [three] = resolve([BOOST], [], true, 3)
    expect(hp.gridValues(three)).toEqual([0, 2, 4])
  })

  it('tests all the testable values without an entry, and a boolean tests true and false', () => {
    const flag = { name: 'flag', type: 'boolean', promoted_value: true }
    const [field, bool] = resolve([FIELD, flag])
    expect(field.values_to_test).toEqual({ type: 'set', values: ['name.text', 'name.ngram'] })
    expect(bool.values_to_test).toEqual({ type: 'set', values: [true, false] })
  })

  it('caps random search at the sample size or the finite space', () => {
    expect(hp.countVariants(resolve([BOOST], STEP_1), 'random', 3)).toBe(3)
    const small = { name: 'n', type: 'number', promoted_value: 1, testable_values: { type: 'range', min: 1, max: 2 } }
    const entries = [{ name: 'n', values: { type: 'range', min: 1, max: 2, step: 1 } }]
    expect(hp.countVariants(resolve([small], entries), 'random', 50)).toBe(2)
    // A range without a step is continuous
    expect(hp.countVariants(resolve([BOOST]), 'random', 50)).toBe(50)
  })

  it('counts one variant for a strategy without hyperparameters', () => {
    expect(hp.countVariants([], 'grid')).toBe(1)
  })

  it('keeps every hyperparameter at its promoted value without optimization', () => {
    expect(hp.countVariants(resolve([BOOST, FIELD], [], false), 'grid')).toBe(1)
  })

  it('narrows the values to test by name, and turns testing off', () => {
    const narrowed = resolve([BOOST], [{ name: 'boost', values: { type: 'set', values: [1, 2, 3] } }])
    expect(hp.countVariants(narrowed, 'grid')).toBe(3)
    const pinned = resolve([BOOST], [{ name: 'boost', enabled: false }])
    expect(pinned[0].values_to_test).toBeNull()
    expect(hp.countVariants(pinned, 'grid')).toBe(1)
  })

  it('prefers the entry scoped to the strategy', () => {
    const entries = [
      { name: 'boost', values: { type: 'set', values: [1, 2] } },
      { name: 'boost', strategy_id: 's1', values: { type: 'set', values: [1, 2, 3] } },
      { name: 'boost', strategy_id: 's2', values: { type: 'set', values: [1] } },
    ]
    expect(hp.countVariants(resolve([BOOST], entries), 'grid')).toBe(3)
  })

  it('needs a finite range to test an unbounded hyperparameter', () => {
    const unbounded = { name: 'boost', type: 'number', promoted_value: 1, testable_values: { type: 'range', min: 0 } }
    expect(() => resolve([unbounded])).toThrow(/unbounded/)
    expect(resolve([unbounded], [{ name: 'boost', values: { type: 'range', min: 0.5, max: 4, log: true } }])).toHaveLength(1)
    expect(resolve([unbounded], [{ name: 'boost', enabled: false }])).toHaveLength(1)
  })

  it('rejects values outside the testable values', () => {
    expect(() => resolve([BOOST], [{ name: 'boost', values: { type: 'range', min: 0, max: 40 } }]))
      .toThrow(/above the valid testable maximum/)
  })

  it('normalizes whole floats so they match the promoted value', () => {
    expect(hp.normalizeValue('number', 2.0)).toBe(2)
    expect(hp.normalizeValue('number', 0.1 + 0.2)).toBe(0.3)
  })
})

describe('optimization settings', () => {
  it('builds no settings when disabled, and null when updating', () => {
    expect(hp.optimizationTaskFromForm(hp.defaultOptimizationForm())).toBeUndefined()
    expect(hp.optimizationTaskFromForm(hp.defaultOptimizationForm(), { forUpdate: true })).toBeNull()
  })

  it('round-trips the form through a task', () => {
    const task = {
      optimization: {
        algorithm: 'random',
        sample_size: 20,
        seed: 'abc',
        points_per_range: 7,
        values_to_test: [
          { name: 'boost', values: { type: 'set', values: [1, 2] } },
          { name: 'field', enabled: false },
          { name: 'boost', strategy_id: 's1', values: { type: 'range', min: 0, max: 4, step: 1 } },
        ],
        objective: { metric: 'mrr', aggregation: 'median' },
        latency_constraint: { stat: 'p90', max_ms: 80 },
        holdout: { ratio: 0.25, seed: 'h' },
      },
    }
    const form = hp.optimizationFormFromTask(task)
    expect(form.enabled).toBe(true)
    expect(form.holdout_percent).toBe(25)
    expect(form.points_per_range).toBe(7)
    expect(form.values_to_test.field).toEqual({ enabled: false, values: undefined })
    const rebuilt = hp.optimizationTaskFromForm(form)
    expect(rebuilt.points_per_range).toBe(7)
    // Entries scoped to a strategy are kept as stored, after the unscoped entries
    expect(rebuilt.values_to_test).toEqual([task.optimization.values_to_test[0], task.optimization.values_to_test[1], task.optimization.values_to_test[2]])
    expect(rebuilt).toEqual(task.optimization)
  })

  it('sends nulls for cleared optional fields on update', () => {
    const form = { ...hp.defaultOptimizationForm(), enabled: true }
    const o = hp.optimizationTaskFromForm(form, { forUpdate: true })
    expect(o.seed).toBeNull()
    expect(o.latency_constraint).toBeNull()
    expect(o.holdout.seed).toBeNull()
    expect(hp.optimizationTaskFromForm(form).latency_constraint).toBeUndefined()
  })

  it('drops unset fields from the values to test and the testable values', () => {
    expect(hp.cleanValuesToTest({ type: 'range', min: 0, max: 1, step: undefined, count: 3, log: false }))
      .toEqual({ type: 'range', min: 0, max: 1, count: 3 })
    expect(hp.cleanTestableValues({ type: 'range', min: 0, max: undefined })).toEqual({ type: 'range', min: 0 })
  })

  it('validates the form', () => {
    const form = { ...hp.defaultOptimizationForm(), enabled: true, latency_enabled: true, latency_max_ms: '' }
    expect(hp.validateOptimizationForm(form)).toEqual([expect.stringMatching(/latency/)])
    expect(hp.validateOptimizationForm({ ...form, latency_enabled: false })).toEqual([])
  })

  it('needs a finite range to test for an unbounded hyperparameter', () => {
    const form = { ...hp.defaultOptimizationForm(), enabled: true }
    const pool = hp.hyperparametersOfPool([{
      hyperparameters: [{ name: 'boost', type: 'number', promoted_value: 1, testable_values: { type: 'range', min: 0 } }],
    }])
    expect(hp.validateOptimizationForm(form, pool)).toEqual([expect.stringMatching(/unbounded/)])
    const narrowed = { ...form, values_to_test: { boost: { enabled: true, values: { type: 'range', min: 0.5, max: 4 } } } }
    expect(hp.validateOptimizationForm(narrowed, pool)).toEqual([])
    const off = { ...form, values_to_test: { boost: { enabled: false } } }
    expect(hp.validateOptimizationForm(off, pool)).toEqual([])
    const outside = { ...form, values_to_test: { boost: { enabled: true, values: { type: 'range', min: -1, max: 4 } } } }
    expect(hp.validateOptimizationForm(outside, pool)).toEqual([expect.stringMatching(/valid testable minimum/)])
  })

  it('describes testable values and values to test', () => {
    expect(hp.describeTestableValues({ type: 'range', min: 0 })).toBe('at least 0')
    expect(hp.describeTestableValues({ type: 'range', max: 5 })).toBe('at most 5')
    expect(hp.describeTestableValues({ type: 'range' })).toBe('any number')
    expect(hp.describeTestableValues({ type: 'range', min: 0, max: 5 })).toBe('0 to 5')
    expect(hp.describeValuesToTest(null)).toBe('Promoted value')
    expect(hp.describeValuesToTest({ type: 'range', min: 1, max: 5, step: 2 })).toBe('1 to 5, step 2')
  })

  it('unions the hyperparameters of a pool and flags type conflicts', () => {
    const pool = hp.hyperparametersOfPool([
      { hyperparameters: [BOOST] },
      { hyperparameters: [{ ...BOOST, type: 'string', promoted_value: 'a', testable_values: { type: 'set', values: ['a', 'b'] } }, FIELD] },
    ])
    expect(pool.map((p) => p.name)).toEqual(['boost', 'field'])
    expect(pool[0].strategies).toBe(2)
    expect(pool[0].hasTypeConflict).toBe(true)
    expect(pool[1].hasTypeConflict).toBe(false)
  })
})

describe('result notices', () => {
  const run = { task: { optimization: { latency_constraint: { stat: 'median', max_ms: 50 } } } }

  it('labels in-sample scores when there is no holdout', () => {
    const notices = hp.optimizationNotices({ variant_count: 5, score_basis: 'in_sample' }, run)
    expect(notices.map((n) => n.type)).toContain('in-sample')
  })

  it('does not label a strategy with a single variant', () => {
    expect(hp.optimizationNotices({ variant_count: 1, score_basis: 'in_sample' }, {})).toEqual([])
  })

  it('warns about low coverage, a small holdout and latency noise', () => {
    const notices = hp.optimizationNotices(
      { variant_count: 5, score_basis: 'holdout', coverage: 0.3 }, run, { holdout: 10 },
    )
    expect(notices.map((n) => n.type)).toEqual(expect.arrayContaining(['low-coverage', 'small-holdout', 'latency-noise']))
    expect(notices.map((n) => n.type)).not.toContain('in-sample')
  })

  it('computes the gain of the winner over the baseline on the headline basis', () => {
    const optimization = {
      score_basis: 'holdout',
      holdout: { metrics: { ndcg: { avg: 0.6 } } },
      baseline_holdout: { metrics: { ndcg: { avg: 0.5 } } },
      tuning: { metrics: { ndcg: { avg: 0.9 } } },
      baseline_tuning: { metrics: { ndcg: { avg: 0.5 } } },
    }
    const gain = hp.winnerGain(optimization, { metric: 'ndcg', aggregation: 'mean' })
    expect(gain.delta).toBeCloseTo(0.1)
    expect(hp.winnerGain({ score_basis: 'holdout' }, { metric: 'ndcg' })).toBeNull()
  })
})

describe('search test inputs', () => {
  const definitions = [
    { name: 'boost', type: 'number', promoted_value: 2, testable_values: { type: 'range', min: 0, max: 5 } },
    { name: 'fuzzy', type: 'boolean', promoted_value: true },
    { name: 'mode', type: 'string', promoted_value: 'and', testable_values: { type: 'set', values: ['and', 'or'] } },
  ]

  test('start at the promoted values', () => {
    const inputs = hp.syncInputs(definitions)
    expect(inputs.boost.raw).toBe('2')
    expect(inputs.fuzzy.raw).toBe(true)
    expect(inputs.mode.raw).toBe('and')
    const parsed = hp.parseInputs(definitions, inputs)
    expect(parsed.values).toEqual({ boost: 2, fuzzy: true, mode: 'and' })
    expect(parsed.errors).toEqual({})
    expect(hp.inputsDiffer(definitions, inputs)).toBe(false)
  })

  test('keep user entries until the definition changes', () => {
    const edited = { ...hp.syncInputs(definitions), boost: { ...hp.syncInputs(definitions).boost, raw: '3' } }
    expect(hp.syncInputs(definitions, edited).boost.raw).toBe('3')
    const changed = definitions.map((d) => d.name === 'boost' ? { ...d, promoted_value: 4 } : d)
    expect(hp.syncInputs(changed, edited).boost.raw).toBe('4')
    expect(hp.inputsDiffer(definitions, edited)).toBe(true)
  })

  test('block on invalid entries and warn on values outside the testable values', () => {
    const inputs = hp.syncInputs(definitions)
    inputs.boost.raw = ''
    expect(hp.parseInputs(definitions, inputs).errors.boost).toBeTruthy()
    inputs.boost.raw = '9'
    const parsed = hp.parseInputs(definitions, inputs)
    expect(parsed.errors).toEqual({})
    expect(parsed.values.boost).toBe(9)
    expect(parsed.warnings.boost).toMatch(/Outside/)
  })
})

describe('inputsFromValues', () => {
  test('set the inputs to the values and keep the rest at the promoted values', () => {
    const definitions = [
      { name: 'boost', type: 'number', promoted_value: 2, testable_values: { type: 'range', min: 0, max: 5 } },
      { name: 'fuzzy', type: 'boolean', promoted_value: true },
    ]
    const inputs = hp.inputsFromValues(definitions, { boost: 4.5, other: 1 })
    expect(inputs.boost.raw).toBe('4.5')
    expect(inputs.fuzzy.raw).toBe(true)
    expect(hp.parseInputs(definitions, inputs).values).toEqual({ boost: 4.5, fuzzy: true })
    // The values survive a sync while the definitions don't change
    expect(hp.syncInputs(definitions, inputs).boost.raw).toBe('4.5')
  })
})
