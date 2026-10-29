/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

/**
 * Pure helpers of the Benchmark tab of the strategy editor. The tab runs an
 * ephemeral benchmark of the draft strategy across scenarios, and compares it
 * against the saved strategy.
 */

import {
  defaultOptimizationForm,
  definitionsForSave,
  extractScenarioParams,
  isOptimizedRun,
  optimizationTaskFromForm,
} from './hyperparameters'

export const DEFAULT_METRICS = ['ndcg', 'precision', 'recall']
export const DEFAULT_K = 10

/**
 * The _id of the draft in a run. Strategy IDs can't contain `~`.
 */
export const draftIdOf = (strategyId) => `${strategyId}_draft`

export const defaultEditorForm = () => ({
  metrics: [...DEFAULT_METRICS],
  k: DEFAULT_K,
  scenario_tags: [],
  optimization: { ...defaultOptimizationForm(), enabled: false },
})

/**
 * A strategy doc to pass inline to a run.
 */
export const strategyDoc = (_id, { name, tags, source, hyperparameters }) => ({
  _id,
  _source: {
    name,
    tags: tags || [],
    params: extractScenarioParams(source || ''),
    template: { source: source || '' },
    hyperparameters: definitionsForSave(hyperparameters || []),
  },
})

/**
 * Whether the run tests hyperparameter values: the switch is on and the draft
 * has hyperparameters to test.
 */
export const testsHyperparameters = (form, draft) =>
  Boolean(form?.optimization?.enabled) && (draft?.hyperparameters || []).length > 0

/**
 * Build the task of an editor benchmark.
 *
 * `saved` and `draft` are `{ name, tags, source, hyperparameters }`. When
 * `compare` is set, the run has both strategies: the saved one under
 * `strategyId` and the draft under `draftIdOf(strategyId)`. Otherwise the run
 * has only the draft, under `strategyId`.
 *
 * With hyperparameter testing, the saved strategy keeps its promoted values,
 * through `values_to_test` entries scoped to it, so it stays the one variant
 * the user has today.
 */
export const buildEditorTask = ({ strategyId, saved, draft, form, compare }) => {
  const docs = compare
    ? [strategyDoc(strategyId, saved), strategyDoc(draftIdOf(strategyId), draft)]
    : [strategyDoc(strategyId, draft)]
  const task = {
    metrics: [...(form.metrics || [])],
    k: parseInt(form.k) || DEFAULT_K,
    strategies: { docs },
    scenarios: {},
  }
  if (form.scenario_tags?.length)
    task.scenarios.tags = [...form.scenario_tags]
  if (testsHyperparameters(form, draft)) {
    const optimization = optimizationTaskFromForm({ ...form.optimization, enabled: true })
    if (compare) {
      const scoped = (saved.hyperparameters || [])
        .filter((h) => h.name)
        .map((h) => ({ name: h.name, strategy_id: strategyId, enabled: false }))
      optimization.values_to_test = [
        ...optimization.values_to_test.filter((e) => e.strategy_id !== strategyId),
        ...scoped,
      ]
    }
    task.optimization = optimization
  }
  return task
}

/**
 * Validate the form. Returns a list of error messages.
 */
export const validateEditorForm = (form, draft) => {
  const errors = []
  if (!form.metrics?.length)
    errors.push('Choose at least one metric.')
  if (!(parseInt(form.k) >= 1))
    errors.push('k must be at least 1.')
  if (testsHyperparameters(form, draft) && !form.metrics?.includes(form.optimization.objective_metric))
    errors.push('The objective metric must be one of the chosen metrics.')
  return errors
}

/**
 * The basis of the headline scores of a run: `holdout` when the draft's
 * winner was validated on held out scenarios, `in_sample` when the run tuned
 * hyperparameters without a holdout, and `all` when it tuned nothing.
 */
export const scoreBasis = (run, draftId) => {
  if (!isOptimizedRun(run))
    return 'all'
  return run?.summary?.strategy_id?.[draftId]?.optimization?.score_basis === 'holdout' ? 'holdout' : 'in_sample'
}

const avgOf = (block, metric) => {
  const value = block?.metrics?.[metric]?.avg
  return value === undefined ? null : value
}

/**
 * The headline score of each metric for the draft and the saved strategy.
 * `savedId` is null when the run has only the draft. Returns
 * `[{ metric, saved, draft, delta }]`.
 */
export const compareStrategies = (run, savedId, draftId, metrics) => {
  const byId = run?.summary?.strategy_id || {}
  return (metrics || []).map((metric) => {
    const draft = avgOf(byId[draftId]?._total, metric)
    const saved = savedId ? avgOf(byId[savedId]?._total, metric) : null
    const delta = draft !== null && saved !== null ? draft - saved : null
    return { metric, saved, draft, delta }
  })
}

/**
 * The headline score of each metric for the draft's best variant and its
 * baseline variant, which uses the promoted values. The scores are on the
 * holdout when the run has one. Returns `[{ metric, saved, draft, delta }]`,
 * where `saved` is the baseline, like `compareStrategies`.
 */
export const compareWinnerToBaseline = (run, draftId, metrics) => {
  const optimization = run?.summary?.strategy_id?.[draftId]?.optimization
  const holdout = optimization?.score_basis === 'holdout'
  const best = holdout ? optimization?.holdout : optimization?.tuning
  const baseline = holdout ? optimization?.baseline_holdout : optimization?.baseline_tuning
  return (metrics || []).map((metric) => {
    const draft = avgOf(best, metric)
    const saved = avgOf(baseline, metric)
    const delta = draft !== null && saved !== null ? draft - saved : null
    return { metric, saved, draft, delta }
  })
}

/**
 * The score of each scenario for one metric, for the draft and the saved
 * strategy. Returns `[{ scenario_id, name, values, split, saved, draft, delta }]`,
 * with the biggest regressions first, or the weakest draft scores first when
 * the run has only the draft.
 */
export const compareScenarios = (run, savedId, draftId, metric) => {
  const byId = run?.summary?.strategy_id || {}
  const draftBy = byId[draftId]?.by_scenario_id || {}
  const savedBy = savedId ? (byId[savedId]?.by_scenario_id || {}) : {}
  const runtime = run?.runtime?.scenarios || {}
  const ids = Array.from(new Set([...Object.keys(draftBy), ...Object.keys(savedBy)]))
  const rows = ids.map((id) => {
    const draft = avgOf(draftBy[id], metric)
    const saved = savedId ? avgOf(savedBy[id], metric) : null
    return {
      scenario_id: id,
      name: runtime[id]?.name || id,
      values: runtime[id]?.values,
      split: runtime[id]?._split || null,
      saved,
      draft,
      delta: draft !== null && saved !== null ? draft - saved : null,
    }
  })
  const key = savedId ? 'delta' : 'draft'
  return rows.sort((a, b) => {
    if (a[key] === null) return 1
    if (b[key] === null) return -1
    return a[key] - b[key] || a.name.localeCompare(b.name)
  })
}

/**
 * The number of judged scenarios of a run, split into tuning and holdout.
 * Scenarios without judgements have no split, because they didn't run.
 */
export const scenarioCounts = (run) => {
  const counts = { tuning: 0, holdout: 0, total: 0 }
  for (const scenario of Object.values(run?.runtime?.scenarios || {})) {
    if (scenario._split === 'holdout') counts.holdout += 1
    else if (scenario._split === 'tuning') counts.tuning += 1
  }
  counts.total = counts.tuning + counts.holdout
  return counts
}

/**
 * The draft's variants of a run, by rank.
 */
export const draftVariants = (run, draftId) =>
  (run?.variants || [])
    .filter((v) => v.strategy_id === draftId)
    .sort((a, b) => (a.rank ?? Infinity) - (b.rank ?? Infinity))

/**
 * A key of everything a run depends on. Results are out of date once the
 * current key differs from the key of the run.
 */
export const staleKey = ({ saved, draft, form }) => JSON.stringify({
  saved: saved ? [saved.source, definitionsForSave(saved.hyperparameters || [])] : null,
  draft: [draft?.source, definitionsForSave(draft?.hyperparameters || [])],
  form,
})

export default {
  DEFAULT_K,
  DEFAULT_METRICS,
  buildEditorTask,
  compareScenarios,
  compareStrategies,
  compareWinnerToBaseline,
  defaultEditorForm,
  draftIdOf,
  draftVariants,
  scenarioCounts,
  scoreBasis,
  staleKey,
  strategyDoc,
  testsHyperparameters,
  validateEditorForm,
}
