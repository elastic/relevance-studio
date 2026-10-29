/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

/**
 * Hyperparameter helpers shared by the strategy editor, the benchmark editor
 * and the run view. These mirror the server rules in
 * `src/server/models/hyperparameters.py`, `src/server/api/optimization.py`
 * and `src/server/utils.py`. The server stays the source of truth: the UI uses
 * these helpers for instant feedback and live variant counts only.
 */

export const HYPERPARAMETER_NAMESPACE = 'hp'
export const HYPERPARAMETER_TYPES = ['number', 'string', 'boolean']
export const RE_NAME = /^\w+$/

export const DEFAULT_SAMPLE_SIZE = 50
export const DEFAULT_POINTS_PER_RANGE = 5
export const MIN_STABLE_HOLDOUT_SCENARIOS = 30
export const LOW_COVERAGE_THRESHOLD = 0.5

const RE_REFS = /{{\s*hp\.(\w+)\s*}}|{{\s*#\s*toJson\s*}}\s*hp\.(\w+)\s*{{\s*\/\s*toJson\s*}}/g
const RE_PARAMS = /{{\s*([\w.-]+)\s*}}/g
const RE_UNSAFE_STRING = /["\\\u0000-\u001f]/

const isSet = (value) => value !== undefined && value !== null
const isNumeric = (type) => type === 'number'

////  Template references  //////////////////////////////////////////////////

/**
 * Names of the hyperparameters a template references, as `{{hp.name}}` or
 * `{{#toJson}}hp.name{{/toJson}}`. Sorted and unique.
 */
export const extractRefs = (source) => {
  const names = new Set()
  for (const match of (source || '').matchAll(RE_REFS))
    names.add(match[1] || match[2])
  return Array.from(names).sort()
}

/**
 * Scenario params (Mustache variables) of a template, excluding
 * hyperparameter references, which scenarios don't provide.
 */
export const extractScenarioParams = (source) => {
  const params = new Set()
  for (const match of (source || '').matchAll(RE_PARAMS)) {
    if (!match[1].startsWith(`${HYPERPARAMETER_NAMESPACE}.`))
      params.add(match[1])
  }
  return Array.from(params)
}

////  Values  ////////////////////////////////////////////////////////////////

/**
 * Whether a value fits a hyperparameter type. Booleans are not numbers.
 */
export const checkValueType = (type, value) => {
  if (type === 'boolean')
    return typeof value === 'boolean'
  if (type === 'number')
    return typeof value === 'number' && Number.isFinite(value)
  if (type === 'string')
    return typeof value === 'string'
  return false
}

/**
 * Normalize a value into its canonical form, as the server does, so that
 * floating point noise (0.30000000000000004) doesn't create distinct values.
 */
export const normalizeValue = (type, value, log = false) => {
  if (type === 'number')
    return log ? Number(Number(value).toPrecision(6)) : Number(Number(value).toFixed(10))
  if (type === 'boolean')
    return Boolean(value)
  return String(value)
}

/**
 * Parse text typed by a user into a value of the given type.
 * Returns undefined when the text doesn't fit the type.
 */
export const parseValue = (type, text) => {
  if (type === 'string')
    return String(text)
  if (type === 'boolean') {
    if (text === true || text === 'true') return true
    if (text === false || text === 'false') return false
    return undefined
  }
  if (text === '' || text === null || text === undefined)
    return undefined
  const n = Number(text)
  return Number.isFinite(n) ? n : undefined
}

export const formatValue = (value) => {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number')
    return Number.isInteger(value) ? String(value) : String(Number(value.toPrecision(6)))
  return String(value)
}

const valueKey = (value) => `${typeof value}:${value}`

const distinctCount = (values) => new Set(values.map(valueKey)).size

/**
 * Promoted values of a list of hyperparameter definitions, by name.
 */
export const promotedValues = (definitions) => {
  const values = {}
  for (const hp of definitions || [])
    values[hp.name] = hp.promoted_value
  return values
}

/**
 * Whether a value is one of the valid testable values. Without testable
 * values (a boolean), any value of the type is valid.
 */
export const valueIsTestable = (type, value, testable) => {
  if (!checkValueType(type, value))
    return false
  if (!testable)
    return true
  if (testable.type === 'set')
    return (testable.values || []).some((v) => valueKey(v) === valueKey(value))
  if (isSet(testable.min) && value < testable.min)
    return false
  if (isSet(testable.max) && value > testable.max)
    return false
  return true
}

/**
 * Render only the `{{hp.*}}` tags of a template with values (the production
 * template). Other Mustache tags stay in place. Throws if a referenced
 * hyperparameter has no value.
 */
export const renderHyperparameters = (source, values) => {
  const need = (name) => {
    if (!(name in values))
      throw new Error(`No value for hyperparameter '${name}'`)
    return values[name]
  }
  const scalar = (value) => {
    if (typeof value === 'boolean' || typeof value === 'number')
      return JSON.stringify(value)
    return JSON.stringify(String(value)).slice(1, -1)
  }
  return (source || '')
    .replace(/{{\s*#\s*toJson\s*}}\s*hp\.(\w+)\s*{{\s*\/\s*toJson\s*}}/g, (_, name) => JSON.stringify(need(name)))
    .replace(/{{\s*hp\.(\w+)\s*}}/g, (_, name) => scalar(need(name)))
}

/**
 * Render a template for one search: bind hyperparameter values, then scenario
 * values, and parse the result. Throws on invalid JSON.
 */
export const applyTemplate = (source, scenarioValues, hyperparameterValues) => {
  const withHp = renderHyperparameters(source, hyperparameterValues || {})
  const rendered = withHp.replace(/{{\s*([\w.-]+)\s*}}/g, (_, key) => scenarioValues?.[key])
  return JSON.parse(rendered)
}

////  Validation  ////////////////////////////////////////////////////////////

const checkSetValues = (type, values) => {
  if (!Array.isArray(values) || distinctCount(values) < 2)
    return 'A set needs at least two distinct values'
  const bad = values.find((v) => !checkValueType(type, v))
  if (bad !== undefined)
    return `Value ${JSON.stringify(bad)} is not a valid ${type}`
  if (type === 'string' && values.some((v) => RE_UNSAFE_STRING.test(v)))
    return `Values can't contain quotes, backslashes or control characters`
  return null
}

/**
 * Validate the valid testable values of a strategy's hyperparameter.
 * A range may leave either bound open. A boolean always has the values true
 * and false, so it has none to validate. Returns an error message, or null.
 */
export const validateTestableValues = (type, testable) => {
  if (type === 'boolean')
    return null
  if (!testable)
    return 'Valid testable values are required'
  if (testable.type === 'set')
    return checkSetValues(type, testable.values)
  if (testable.type === 'range') {
    if (!isNumeric(type))
      return `A range needs the number type, not ${type}`
    for (const field of ['min', 'max']) {
      if (isSet(testable[field]) && !Number.isFinite(testable[field]))
        return `The ${field === 'min' ? 'minimum' : 'maximum'} must be a number`
    }
    if (isSet(testable.min) && isSet(testable.max) && !(testable.min < testable.max))
      return 'The minimum must be less than the maximum'
    return null
  }
  return 'Unknown type of testable values'
}

/**
 * Validate the values a benchmark tests for a hyperparameter against the
 * hyperparameter's type and valid testable values. Returns an error message,
 * or null.
 */
export const validateValuesToTest = (type, testable, spec) => {
  if (!spec)
    return null
  if (spec.type === 'set') {
    const error = checkSetValues(type, spec.values)
    if (error)
      return error
    const outside = spec.values.find((v) => !valueIsTestable(type, v, testable))
    return outside === undefined ? null : `${JSON.stringify(outside)} is not one of the valid testable values`
  }
  if (spec.type === 'range') {
    if (!isNumeric(type))
      return `A range needs the number type, not ${type}`
    if (testable?.type === 'set')
      return `A range isn't allowed because the valid testable values are a set`
    const { min, max, step, count, log } = spec
    if (!Number.isFinite(min) || !Number.isFinite(max))
      return 'A range needs a minimum and a maximum'
    if (!(min < max))
      return 'The minimum must be less than the maximum'
    if (isSet(step) && isSet(count))
      return 'Use either step or count, not both'
    if (isSet(step) && !(step > 0))
      return 'The step must be above 0'
    if (isSet(count) && !(Number.isInteger(count) && count >= 2))
      return 'The count must be a whole number of at least 2'
    if (log && min <= 0)
      return 'A log range needs a minimum above 0'
    if (log && isSet(step))
      return 'A log range uses count instead of step'
    if (isSet(testable?.min) && min < testable.min)
      return `The minimum is below the valid testable minimum of ${formatValue(testable.min)}`
    if (isSet(testable?.max) && max > testable.max)
      return `The maximum is above the valid testable maximum of ${formatValue(testable.max)}`
    return null
  }
  return 'Unknown type of values to test'
}

/**
 * Validate hyperparameter definitions against a template source.
 * Errors block saving. Warnings don't.
 */
export const validateDefinitions = (definitions, source) => {
  const errors = []
  const warnings = []
  const seen = new Set()
  for (const hp of definitions || []) {
    const label = hp.name || '(unnamed)'
    if (!RE_NAME.test(hp.name || '')) {
      errors.push(`Hyperparameter '${label}' needs a name of letters, digits and underscores`)
      continue
    }
    if (seen.has(hp.name))
      errors.push(`Hyperparameter '${hp.name}' is defined more than once`)
    seen.add(hp.name)
    if (!HYPERPARAMETER_TYPES.includes(hp.type)) {
      errors.push(`Hyperparameter '${hp.name}' needs a type`)
      continue
    }
    const valid = isSet(hp.promoted_value) && checkValueType(hp.type, hp.promoted_value)
    if (!valid)
      errors.push(`The promoted value of '${hp.name}' must be a valid ${hp.type}`)
    else if (hp.type === 'string' && RE_UNSAFE_STRING.test(hp.promoted_value))
      errors.push(`The promoted value of '${hp.name}' can't contain quotes, backslashes or control characters`)
    const testableError = validateTestableValues(hp.type, hp.testable_values)
    if (testableError)
      errors.push(`Valid testable values of '${hp.name}': ${testableError}`)
    else if (valid && !valueIsTestable(hp.type, hp.promoted_value, hp.type === 'boolean' ? null : hp.testable_values))
      errors.push(`The promoted value of '${hp.name}' must be one of its valid testable values`)
  }
  const refs = extractRefs(source)
  for (const name of refs) {
    if (!seen.has(name))
      errors.push(`The template references '{{hp.${name}}}', which isn't defined`)
  }
  for (const name of seen) {
    if (!refs.includes(name))
      warnings.push(`Hyperparameter '${name}' isn't used in the template`)
  }
  return { errors, warnings }
}

////  Values to test and variant counts  /////////////////////////////////////

const implicitTestable = (hp) =>
  hp.type === 'boolean' ? { type: 'set', values: [true, false] } : hp.testable_values

/**
 * Resolve the effective hyperparameters of a strategy for a benchmark, as the
 * server does. `entries` is the benchmark's `values_to_test` list of
 * `{name, strategy_id?, enabled?, values?}`. A hyperparameter tests its entry
 * (one scoped to the strategy wins), or else all of its valid testable
 * values. Without `optimize`, or with `enabled` false, it keeps its promoted
 * value (`values_to_test` is null). Throws for values that fall outside the
 * valid testable values, and for an unbounded range with no finite range to
 * test.
 */
export const resolveHyperparameters = (
  definitions,
  entries = [],
  strategyId = null,
  pointsPerRange = DEFAULT_POINTS_PER_RANGE,
  optimize = true,
) => {
  const find = (name) => (entries || []).find((e) => e.name === name && e.strategy_id === strategyId && strategyId)
    || (entries || []).find((e) => e.name === name && !e.strategy_id)
  return (definitions || []).map((definition) => {
    const hp = { ...definition, testable_values: implicitTestable(definition) }
    const entry = find(hp.name)
    let values
    if (!optimize || (entry && entry.enabled === false)) {
      values = null
    } else if (entry?.values) {
      const error = validateValuesToTest(hp.type, hp.testable_values, entry.values)
      if (error)
        throw new Error(`Values to test for '${hp.name}': ${error}`)
      values = { ...entry.values }
    } else if (hp.testable_values.type === 'set') {
      values = { type: 'set', values: [...hp.testable_values.values] }
    } else if (!isSet(hp.testable_values.min) || !isSet(hp.testable_values.max)) {
      throw new Error(
        `The valid testable values of '${hp.name}' are unbounded. Set a finite range to test, or turn off testing it.`
      )
    } else {
      values = { type: 'range', min: hp.testable_values.min, max: hp.testable_values.max }
    }
    if (values?.type === 'range') {
      values.log = Boolean(values.log)
      if (!isSet(values.step) && !isSet(values.count))
        values.count = pointsPerRange
    }
    return { ...hp, values_to_test: values }
  })
}

const dedupe = (values) => {
  const seen = new Set()
  return values.filter((v) => {
    const key = JSON.stringify(v)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

/**
 * Every value a hyperparameter tests, for grid search. A hyperparameter that
 * keeps its promoted value contributes only that value.
 */
export const gridValues = (hp) => {
  const spec = hp.values_to_test
  if (!spec)
    return [normalizeValue(hp.type, hp.promoted_value)]
  if (spec.type === 'set')
    return dedupe(spec.values.map((v) => normalizeValue(hp.type, v)))
  const { min: lo, max: hi, step } = spec
  const count = spec.count || DEFAULT_POINTS_PER_RANGE
  const log = Boolean(spec.log)
  let values
  if (isSet(step)) {
    const n = Math.floor((hi - lo) / step + 1e-9) + 1
    values = Array.from({ length: n }, (_, i) => lo + i * step)
  } else if (count === 1 || lo === hi) {
    values = [lo]
  } else if (log) {
    values = Array.from({ length: count }, (_, i) => lo * Math.pow(hi / lo, i / (count - 1)))
  } else {
    values = Array.from({ length: count }, (_, i) => lo + (hi - lo) * i / (count - 1))
  }
  return dedupe(values.map((v) => normalizeValue(hp.type, v, log)))
}

const finiteSize = (hp) => {
  const spec = hp.values_to_test
  if (!spec)
    return 1
  if (spec.type === 'set')
    return dedupe(spec.values.map((v) => normalizeValue(hp.type, v))).length
  if (isSet(spec.step))
    return Math.floor((spec.max - spec.min) / spec.step + 1e-9) + 1
  return Infinity
}

/**
 * Number of variants a search produces. The baseline variant always counts.
 */
export const countVariants = (resolved, algorithm = 'grid', sampleSize = DEFAULT_SAMPLE_SIZE) => {
  if (!resolved?.length)
    return 1
  if (algorithm === 'grid') {
    const grids = resolved.map(gridValues)
    const total = grids.reduce((n, g) => n * g.length, 1)
    const inGrid = resolved.every((hp, i) => {
      const promoted = JSON.stringify(normalizeValue(hp.type, hp.promoted_value))
      return grids[i].some((v) => JSON.stringify(v) === promoted)
    })
    return inGrid ? total : total + 1
  }
  const size = resolved.reduce((n, hp) => n * finiteSize(hp), 1)
  return Math.min(sampleSize, size)
}

/**
 * Drop unset fields of testable values so the server accepts them. A boolean
 * has none, because the server always assigns true and false.
 */
export const cleanTestableValues = (testable) => {
  if (!testable)
    return null
  if (testable.type === 'set')
    return { type: 'set', values: testable.values || [] }
  const out = { type: 'range' }
  if (isSet(testable.min)) out.min = testable.min
  if (isSet(testable.max)) out.max = testable.max
  return out
}

/**
 * Drop unset fields of the values to test so the server accepts them.
 */
export const cleanValuesToTest = (spec) => {
  if (!spec)
    return null
  if (spec.type === 'set')
    return { type: 'set', values: spec.values || [] }
  const out = { type: 'range', min: spec.min, max: spec.max }
  if (isSet(spec.step)) out.step = spec.step
  if (isSet(spec.count)) out.count = spec.count
  if (spec.log) out.log = true
  return out
}

/**
 * Hyperparameter definitions ready to save: clean testable values.
 */
export const definitionsForSave = (definitions) => {
  return (definitions || []).map((hp) => {
    const out = { name: hp.name, type: hp.type, promoted_value: hp.promoted_value }
    if (hp.type !== 'boolean') {
      const testable = cleanTestableValues(hp.testable_values)
      if (testable)
        out.testable_values = testable
    }
    return out
  })
}

/**
 * Whether two lists of definitions are the same once cleaned.
 */
export const sameDefinitions = (a, b) =>
  JSON.stringify(definitionsForSave(a)) === JSON.stringify(definitionsForSave(b))

/**
 * Describe valid testable values in a few words, e.g. `at least 0`.
 */
export const describeTestableValues = (testable) => {
  if (!testable)
    return 'None'
  if (testable.type === 'set')
    return `{${testable.values.map(formatValue).join(', ')}}`
  if (isSet(testable.min) && isSet(testable.max))
    return `${formatValue(testable.min)} to ${formatValue(testable.max)}`
  if (isSet(testable.min))
    return `at least ${formatValue(testable.min)}`
  if (isSet(testable.max))
    return `at most ${formatValue(testable.max)}`
  return 'any number'
}

/**
 * Describe the values a benchmark tests, e.g. `0.1 to 5, step 0.5`. A
 * hyperparameter that keeps its promoted value reads `Promoted value`.
 */
export const describeValuesToTest = (spec) => {
  if (!spec)
    return 'Promoted value'
  if (spec.type === 'set')
    return `{${spec.values.map(formatValue).join(', ')}}`
  let text = `${formatValue(spec.min)} to ${formatValue(spec.max)}`
  if (isSet(spec.step)) text += `, step ${formatValue(spec.step)}`
  else if (isSet(spec.count)) text += `, ${spec.count} values`
  if (spec.log) text += ' (log)'
  return text
}

////  Test inputs  ///////////////////////////////////////////////////////////

/**
 * The raw form value of a hyperparameter value. Booleans stay booleans. Other
 * values become text, so a user can type them.
 */
const rawFromValue = (type, value) =>
  type === 'boolean' ? value === true : formatValue(value)

/**
 * The inputs of a search test, one per hyperparameter, by name. Each input
 * starts at the promoted value. An input keeps what the user entered until the
 * type or promoted value of its definition changes.
 */
export const syncInputs = (definitions, previous = {}) => {
  const inputs = {}
  for (const hp of definitions || []) {
    if (!hp.name)
      continue
    const before = previous[hp.name]
    const unchanged = before && before.type === hp.type && before.promoted === hp.promoted_value
    inputs[hp.name] = unchanged
      ? before
      : { type: hp.type, promoted: hp.promoted_value, raw: rawFromValue(hp.type, hp.promoted_value) }
  }
  return inputs
}

/**
 * The inputs of a search test set to the given values by name, for example
 * the values of a variant. Hyperparameters without a value start at their
 * promoted value.
 */
export const inputsFromValues = (definitions, values = {}) => {
  const inputs = syncInputs(definitions)
  for (const hp of definitions || []) {
    if (inputs[hp.name] && values[hp.name] !== undefined)
      inputs[hp.name] = { ...inputs[hp.name], raw: rawFromValue(hp.type, values[hp.name]) }
  }
  return inputs
}

/**
 * Whether any input differs from its promoted value.
 */
export const inputsDiffer = (definitions, inputs) =>
  (definitions || []).some((hp) => {
    const input = inputs[hp.name]
    return input && input.raw !== rawFromValue(hp.type, hp.promoted_value)
  })

/**
 * Parse the inputs of a search test. Returns the typed `values` by name, an
 * `errors` message by name for inputs that block the test, and a `warnings`
 * message by name for values outside the valid testable values, which don't.
 */
export const parseInputs = (definitions, inputs) => {
  const values = {}
  const errors = {}
  const warnings = {}
  for (const hp of definitions || []) {
    if (!hp.name || !HYPERPARAMETER_TYPES.includes(hp.type))
      continue
    const input = inputs[hp.name]
    if (!input)
      continue
    const value = parseValue(hp.type, input.raw)
    if (value === undefined || (hp.type === 'string' && input.raw === '')) {
      errors[hp.name] = `Enter a ${hp.type === 'number' ? 'number' : 'value'}`
      continue
    }
    if (hp.type === 'string' && RE_UNSAFE_STRING.test(value)) {
      errors[hp.name] = `Can't contain quotes, backslashes or control characters`
      continue
    }
    values[hp.name] = value
    const testable = hp.type === 'boolean' ? null : hp.testable_values
    if (testable && !validateTestableValues(hp.type, testable) && !valueIsTestable(hp.type, value, testable))
      warnings[hp.name] = `Outside the valid testable values (${describeTestableValues(testable)})`
  }
  return { values, errors, warnings }
}

////  Optimization settings (form <-> task)  /////////////////////////////////

export const defaultOptimizationForm = () => ({
  enabled: false,
  algorithm: 'grid',
  sample_size: DEFAULT_SAMPLE_SIZE,
  seed: '',
  points_per_range: DEFAULT_POINTS_PER_RANGE,
  // Unscoped entries by hyperparameter name: { enabled, values }
  values_to_test: {},
  // Entries scoped to a strategy are kept as stored, because the form doesn't edit them
  scoped_values_to_test: [],
  objective_metric: 'ndcg',
  objective_aggregation: 'mean',
  latency_enabled: false,
  latency_stat: 'median',
  latency_max_ms: '',
  holdout_percent: 20,
  holdout_seed: '',
})

/**
 * Build the form state of the optimization settings from a stored task.
 */
export const optimizationFormFromTask = (task) => {
  const form = defaultOptimizationForm()
  const o = task?.optimization
  if (!o)
    return form
  form.enabled = true
  form.algorithm = o.algorithm || 'grid'
  form.sample_size = o.sample_size ?? DEFAULT_SAMPLE_SIZE
  form.seed = o.seed || ''
  form.points_per_range = o.points_per_range ?? DEFAULT_POINTS_PER_RANGE
  for (const entry of o.values_to_test || []) {
    if (entry.strategy_id)
      form.scoped_values_to_test.push(entry)
    else
      form.values_to_test[entry.name] = { enabled: entry.enabled !== false, values: entry.values }
  }
  form.objective_metric = o.objective?.metric || 'ndcg'
  form.objective_aggregation = o.objective?.aggregation || 'mean'
  if (o.latency_constraint) {
    form.latency_enabled = true
    form.latency_stat = o.latency_constraint.stat || 'median'
    form.latency_max_ms = o.latency_constraint.max_ms
  }
  form.holdout_percent = Math.round((o.holdout?.ratio || 0) * 100)
  form.holdout_seed = o.holdout?.seed || ''
  return form
}

/**
 * The `values_to_test` list of a task from the form state.
 */
export const valuesToTestFromForm = (form) => {
  const entries = []
  for (const [name, entry] of Object.entries(form?.values_to_test || {})) {
    const out = { name }
    const values = cleanValuesToTest(entry.values)
    if (entry.enabled === false)
      out.enabled = false
    if (values)
      out.values = values
    if (entry.enabled === false || values)
      entries.push(out)
  }
  return [...entries, ...(form?.scoped_values_to_test || [])]
}

/**
 * Build the `task.optimization` object from the form state.
 *
 * With optimization disabled this returns undefined, or null when `forUpdate`
 * is set, which clears the stored settings. With `forUpdate`, unset optional
 * fields (the seeds and the latency constraint) are null so that an update
 * clears their stored values.
 */
export const optimizationTaskFromForm = (form, { forUpdate = false } = {}) => {
  if (!form?.enabled)
    return forUpdate ? null : undefined
  const o = {
    algorithm: form.algorithm,
    objective: {
      metric: form.objective_metric,
      aggregation: form.objective_aggregation,
    },
    points_per_range: parseInt(form.points_per_range) || DEFAULT_POINTS_PER_RANGE,
    values_to_test: valuesToTestFromForm(form),
    holdout: { ratio: Math.min(0.9, Math.max(0, (Number(form.holdout_percent) || 0) / 100)) },
  }
  if (form.algorithm === 'random')
    o.sample_size = parseInt(form.sample_size) || DEFAULT_SAMPLE_SIZE
  const seed = form.seed !== '' && form.seed !== undefined ? String(form.seed) : undefined
  const holdoutSeed = form.holdout_seed !== '' && form.holdout_seed !== undefined ? String(form.holdout_seed) : undefined
  if (seed !== undefined) o.seed = seed
  else if (forUpdate) o.seed = null
  if (holdoutSeed !== undefined) o.holdout.seed = holdoutSeed
  else if (forUpdate) o.holdout.seed = null
  if (form.latency_enabled && Number(form.latency_max_ms) > 0)
    o.latency_constraint = { stat: form.latency_stat, max_ms: Number(form.latency_max_ms) }
  else if (forUpdate)
    o.latency_constraint = null
  return o
}

/**
 * Validate the optimization form. Returns a list of error messages.
 * `pool` is the union of the hyperparameters of the candidate strategies
 * (see `hyperparametersOfPool`).
 */
export const validateOptimizationForm = (form, pool = []) => {
  const errors = []
  if (!form?.enabled)
    return errors
  if (form.algorithm === 'random' && !(parseInt(form.sample_size) >= 1))
    errors.push('Random search needs a sample size of at least 1')
  if (form.algorithm === 'grid' && !(parseInt(form.points_per_range) >= 2))
    errors.push('Grid search needs at least 2 points per range')
  if (form.latency_enabled && !(Number(form.latency_max_ms) > 0))
    errors.push('The latency constraint needs a maximum above 0')
  const holdout = Number(form.holdout_percent) || 0
  if (holdout < 0 || holdout > 90)
    errors.push('The holdout must be between 0% and 90%')
  for (const hp of pool) {
    const entry = form.values_to_test?.[hp.name]
    if (entry?.enabled === false || hp.hasTypeConflict)
      continue
    const type = hp.types?.[0] || hp.type
    const testable = type === 'boolean' ? null : hp.testable_values
    if (entry?.values) {
      const error = validateValuesToTest(type, testable, entry.values)
      if (error)
        errors.push(`Values to test for '${hp.name}': ${error}`)
    } else if (testable?.type === 'range' && (!isSet(testable.min) || !isSet(testable.max))) {
      errors.push(`'${hp.name}' has unbounded testable values. Set a finite range to test, or turn off testing it.`)
    }
  }
  return errors
}

/**
 * Union of the hyperparameters defined by a pool of strategies, by name.
 * When strategies disagree, the first definition wins. `strategies` counts the
 * strategies that define the name.
 */
export const hyperparametersOfPool = (strategies) => {
  const byName = {}
  for (const strategy of strategies || []) {
    for (const hp of strategy.hyperparameters || []) {
      if (!byName[hp.name])
        byName[hp.name] = { ...hp, testable_values: implicitTestable(hp), strategies: 0, types: new Set() }
      byName[hp.name].strategies += 1
      byName[hp.name].types.add(hp.type)
    }
  }
  return Object.values(byName)
    .map((hp) => ({ ...hp, types: Array.from(hp.types), hasTypeConflict: hp.types.size > 1 }))
    .sort((a, b) => a.name.localeCompare(b.name))
}

////  Results  ///////////////////////////////////////////////////////////////

/**
 * Whether a run optimized hyperparameters (it has a `task.optimization`).
 */
export const isOptimizedRun = (run) => Boolean(run?.task?.optimization)

/**
 * Score a variant's aggregates under an objective. Mirrors the server.
 */
export const objectiveScore = (aggregates, objective) => {
  const metric = aggregates?.metrics?.[objective?.metric]
  if (!metric)
    return null
  // Run summary blocks carry only an average, so fall back to it
  const value = objective?.aggregation === 'median' ? metric.median : metric.avg
  return value === undefined ? (metric.avg ?? null) : value
}

/**
 * Notices that qualify a strategy's optimization result.
 * `optimization` is the strategy's block of the run summary and `run` is the
 * run doc. Each notice has a `type`, `color` and `text`.
 */
export const optimizationNotices = (optimization, run, scenarioCounts = null) => {
  const notices = []
  if (!optimization)
    return notices
  const hasVariants = (optimization.variant_count || 0) > 1
  if (optimization.score_basis === 'in_sample' && hasVariants) {
    notices.push({
      type: 'in-sample',
      color: 'warning',
      text: 'No holdout. The scores are in-sample, so they are optimistic.',
    })
  }
  if (optimization.coverage !== null && optimization.coverage !== undefined
    && optimization.coverage < LOW_COVERAGE_THRESHOLD) {
    notices.push({
      type: 'low-coverage',
      color: 'warning',
      text: `Only ${Math.round(optimization.coverage * 100)}% of the winner's hits have a judgement. Unrated documents count as irrelevant. Judge the unrated documents.`,
    })
  }
  const holdout = scenarioCounts?.holdout
  if (optimization.score_basis === 'holdout' && holdout !== null && holdout !== undefined
    && holdout < MIN_STABLE_HOLDOUT_SCENARIOS) {
    notices.push({
      type: 'small-holdout',
      color: 'warning',
      text: `The holdout has only ${holdout} ${holdout === 1 ? 'scenario' : 'scenarios'}, too few for stable scores.`,
    })
  }
  if (run?.task?.optimization?.latency_constraint && hasVariants) {
    notices.push({
      type: 'latency-noise',
      color: 'primary',
      text: 'Variants run concurrently and compete for resources, so latency comparisons are noisy.',
    })
  }
  if (optimization.no_valid_winner) {
    notices.push({
      type: 'no-valid-winner',
      color: 'warning',
      text: 'No variant satisfies the latency constraint, so the baseline variant is the winner.',
    })
  }
  return notices
}

/**
 * Headline gain of the winner over the baseline on the holdout (or in-sample)
 * for the objective metric. Returns null when it can't be computed.
 */
export const winnerGain = (optimization, objective) => {
  if (!optimization)
    return null
  const hasHoldout = optimization.score_basis === 'holdout'
  const winner = objectiveScore(hasHoldout ? optimization.holdout : optimization.tuning, objective)
  const baseline = objectiveScore(hasHoldout ? optimization.baseline_holdout : optimization.baseline_tuning, objective)
  if (winner === null || baseline === null || winner === undefined || baseline === undefined)
    return null
  return { winner, baseline, delta: winner - baseline }
}

export default {
  DEFAULT_POINTS_PER_RANGE,
  HYPERPARAMETER_NAMESPACE,
  HYPERPARAMETER_TYPES,
  applyTemplate,
  checkValueType,
  cleanTestableValues,
  cleanValuesToTest,
  countVariants,
  defaultOptimizationForm,
  definitionsForSave,
  describeTestableValues,
  describeValuesToTest,
  extractRefs,
  extractScenarioParams,
  formatValue,
  gridValues,
  hyperparametersOfPool,
  inputsDiffer,
  inputsFromValues,
  isOptimizedRun,
  normalizeValue,
  objectiveScore,
  optimizationFormFromTask,
  optimizationNotices,
  optimizationTaskFromForm,
  parseInputs,
  parseValue,
  promotedValues,
  renderHyperparameters,
  resolveHyperparameters,
  sameDefinitions,
  syncInputs,
  validateDefinitions,
  validateOptimizationForm,
  validateTestableValues,
  validateValuesToTest,
  valueIsTestable,
  valuesToTestFromForm,
  winnerGain,
}
