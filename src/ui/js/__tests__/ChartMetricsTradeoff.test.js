/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  buildPlotPoints,
  buildResultsFromEvaluation,
  METRIC_DEFINITIONS,
  metricBetterText,
  pointStyleOverride,
  resolveAxisDefaults,
  resolveAxisDomain,
  spreadPaletteByHue,
} from '../Pages/RunsView/ChartMetricsTradeoff'

// A run's `_total` summary for one strategy, with/without a `took` (latency).
const total = ({ ndcg, took } = {}) => ({
  metrics: {
    ndcg: ndcg === undefined ? undefined : { avg: ndcg, min: ndcg, max: ndcg },
  },
  took: took === undefined ? undefined : { avg: took },
  unrated_docs: { count: 0, percent: 0 },
  by_scenario_id: {},
})

describe('buildResultsFromEvaluation', () => {
  it('omits the latency metric for a strategy whose `took` is missing', () => {
    const evaluation = {
      summary: { strategy_id: { s1: { _total: total({ ndcg: 0.5 }) } } },
      runtime: { strategies: { s1: { name: 'Strategy 1', tags: ['bm25'] } } },
    }
    const [result] = buildResultsFromEvaluation(evaluation)
    expect(result.metrics.ndcg).toEqual({ value: 0.5, rangeLower: 0.5, rangeUpper: 0.5 })
    expect(result.metrics.latency_avg_ms).toBeUndefined()
  })

  it('includes the latency metric for a strategy whose `took` is present', () => {
    const evaluation = {
      summary: { strategy_id: { s1: { _total: total({ ndcg: 0.5, took: 42 }) } } },
      runtime: { strategies: { s1: { name: 'Strategy 1', tags: ['bm25'] } } },
    }
    const [result] = buildResultsFromEvaluation(evaluation)
    expect(result.metrics.latency_avg_ms).toEqual({ value: 42 })
  })
})

describe('resolveAxisDefaults', () => {
  const relevanceOnly = METRIC_DEFINITIONS.filter((m) => m.kind === 'relevance')

  it('defaults to latency on X when available, matching the usual default', () => {
    const { xKey, yKey } = resolveAxisDefaults(METRIC_DEFINITIONS, 'latency_avg_ms', 'ndcg')
    expect(xKey).toBe('latency_avg_ms')
    expect(yKey).toBe('ndcg')
  })

  it('falls back to an available metric when latency is unavailable (took missing)', () => {
    const { xKey, yKey } = resolveAxisDefaults(relevanceOnly, 'latency_avg_ms', 'ndcg')
    expect(xKey).not.toBe('latency_avg_ms')
    expect(relevanceOnly.some((m) => m.key === xKey)).toBe(true)
    expect(yKey).toBe('ndcg')
  })

  it('does not collapse both axes onto the same metric when falling back', () => {
    const { xKey, yKey } = resolveAxisDefaults(relevanceOnly, 'latency_avg_ms', 'ndcg')
    expect(xKey).not.toBe(yKey)
  })

  it('falls back to the first available metric for both axes if nothing else fits', () => {
    const onlyNdcg = METRIC_DEFINITIONS.filter((m) => m.key === 'ndcg')
    const { xKey, yKey } = resolveAxisDefaults(onlyNdcg, 'latency_avg_ms', 'precision')
    expect(xKey).toBe('ndcg')
    expect(yKey).toBe('ndcg')
  })
})

describe('resolveAxisDomain', () => {
  const metric = (key) => METRIC_DEFINITIONS.find((m) => m.key === key)

  it.each(['ndcg', 'precision', 'recall', 'mrr'])(
    'pins the %s axis to the fixed [0, 1] domain regardless of the data',
    (key) => {
      expect(resolveAxisDomain(metric(key), [0.2, 0.3, 0.4], false)).toEqual({ min: 0, max: 1 })
    },
  )

  it('ignores an empty or sparse dataset for a relevance metric', () => {
    expect(resolveAxisDomain(metric('ndcg'), [], false)).toEqual({ min: 0, max: 1 })
  })

  it('computes a padded domain from the data for latency', () => {
    const domain = resolveAxisDomain(metric('latency_avg_ms'), [10, 20, 30], false)
    expect(domain.min).toBeLessThan(10)
    expect(domain.max).toBeGreaterThan(30)
  })

  it('returns undefined for latency with no data, unlike the fixed relevance domain', () => {
    expect(resolveAxisDomain(metric('latency_avg_ms'), [], false)).toBeUndefined()
  })

  it('fits a relevance metric to the data when fitToData is on', () => {
    const domain = resolveAxisDomain(metric('ndcg'), [0.2, 0.3, 0.4], false, true)
    expect(domain).not.toEqual({ min: 0, max: 1 })
    expect(domain.min).toBeLessThan(0.2)
    expect(domain.max).toBeGreaterThan(0.4)
  })

  it('still fits latency to the data when fitToData is on (nothing changes)', () => {
    const domain = resolveAxisDomain(metric('latency_avg_ms'), [10, 20, 30], false, true)
    expect(domain.min).toBeLessThan(10)
    expect(domain.max).toBeGreaterThan(30)
  })
})

describe('metricBetterText', () => {
  const metric = (key) => METRIC_DEFINITIONS.find((m) => m.key === key)

  it('says "(higher is better)" for a higher_is_better metric', () => {
    expect(metricBetterText(metric('ndcg'))).toBe('(higher is better)')
  })

  it('says "(lower is better)" for a lower_is_better metric', () => {
    expect(metricBetterText(metric('latency_avg_ms'))).toBe('(lower is better)')
  })
})

describe('pointStyleOverride', () => {
  const familyColor = () => '#00ff00'
  const familyShape = () => 'circle'

  it('styles a real point by its family', () => {
    const style = pointStyleOverride(
      { datum: { family: 'bm25', dominated: false } },
      familyColor,
      familyShape,
    )
    expect(style).toMatchObject({ shape: 'circle', fill: '#00ff00', opacity: 1 })
  })

  it('dims a dominated point', () => {
    const style = pointStyleOverride(
      { datum: { family: 'bm25', dominated: true } },
      familyColor,
      familyShape,
    )
    expect(style.opacity).toBe(0.35)
  })

  // Regression: dimming must track the "Pareto frontier" switch. Otherwise a
  // run where only one strategy is ever non-dominated never draws a 2+ point
  // frontier line (the switch's other effect) *and* always shows dimming
  // regardless of the switch — so toggling it has no visible effect at all.
  it('does not dim a dominated point when showFrontier is off', () => {
    const style = pointStyleOverride(
      { datum: { family: 'bm25', dominated: true } },
      familyColor,
      familyShape,
      false,
    )
    expect(style.opacity).toBe(1)
  })

  // Regression: Elastic Charts unions x-values across the per-family
  // BubbleSeries (sharing a groupId) and synthesizes gap-filler points with
  // no backing `datum` for any family missing a value at another family's x.
  // Those filler points still pass through this accessor (they're dropped
  // from rendering afterward), so it must not throw — it previously did,
  // crashing the whole chart whenever more than one family had data (e.g.
  // once a run missing `took` no longer defaulted to an all-empty axis).
  it.each([
    ['no datum at all', {}],
    ['a null datum', { datum: null }],
    ['an undefined datum', { datum: undefined }],
  ])('tolerates a synthetic gap-filler point with %s', (_label, datum) => {
    expect(() => pointStyleOverride(datum, familyColor, familyShape)).not.toThrow()
    expect(pointStyleOverride(datum, familyColor, familyShape)).toBeUndefined()
  })
})

describe('spreadPaletteByHue', () => {
  // Regression: `useEuiPaletteColorBlind` pairs a saturated shade of each
  // hue with a lighter shade of that *same* hue (teal, teal, blue, blue,
  // ...), so the first two families — the common case — used to land on two
  // shades of the same color (both teal), which are hard to tell apart.
  it('assigns the first two colors to different hues (not two shades of the same hue)', () => {
    const palette = ['teal-dark', 'teal-light', 'blue-dark', 'blue-light']
    const spread = spreadPaletteByHue(palette)
    expect(spread.slice(0, 2)).toEqual(['teal-dark', 'blue-dark'])
  })

  it('reuses the lighter shades only after every hue is already in use', () => {
    const palette = ['teal-dark', 'teal-light', 'blue-dark', 'blue-light']
    expect(spreadPaletteByHue(palette)).toEqual(['teal-dark', 'blue-dark', 'teal-light', 'blue-light'])
  })

  it('preserves palette length', () => {
    const palette = Array.from({ length: 10 }, (_, i) => `color-${i}`)
    expect(spreadPaletteByHue(palette)).toHaveLength(10)
  })
})

describe('end-to-end: a run missing `took` still renders a non-empty chart', () => {
  it('produces plot points using the relevance-metric fallback axes', () => {
    const evaluation = {
      summary: {
        strategy_id: {
          s1: { _total: total({ ndcg: 0.9 }) },
          s2: { _total: total({ ndcg: 0.4 }) },
        },
      },
      runtime: {
        strategies: {
          s1: { name: 'Strategy 1', tags: ['bm25'] },
          s2: { name: 'Strategy 2', tags: ['elser'] },
        },
      },
    }
    const results = buildResultsFromEvaluation(evaluation)
    const availableMetrics = METRIC_DEFINITIONS.filter(
      (m) => results.some((r) => r.metrics[m.key] !== undefined),
    )
    expect(availableMetrics.some((m) => m.kind === 'latency')).toBe(false)

    const { xKey, yKey } = resolveAxisDefaults(availableMetrics, 'latency_avg_ms', 'ndcg')
    const metricByKey = new Map(METRIC_DEFINITIONS.map((m) => [m.key, m]))
    const points = buildPlotPoints(results, metricByKey.get(xKey), metricByKey.get(yKey), false, false)

    expect(points).toHaveLength(2)
  })
})
