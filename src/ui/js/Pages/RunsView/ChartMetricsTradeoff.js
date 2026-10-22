/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

/**
 * ChartMetricsTradeoff
 *
 * Scatterplot comparing a run's strategies on two user-selected metrics (any
 * relevance metric the run computed, or average latency). One point per
 * strategy, with:
 *   - Pareto frontier (non-dominated strategies) drawn as a step line
 *   - optional min/max range whiskers on both axes (relevance metrics report
 *     a min/max across scenarios; latency only reports an average, so it
 *     never gets whiskers)
 *   - optional log scale on the latency axis
 *   - dominated strategies dimmed
 *   - shape and color encode the strategy's first tag
 *
 * DATA CONTRACT
 * Fed from the same `evaluation` object as TableMetrics/ChartMetricsHeatmap on
 * this page: `evaluation.summary.strategy_id[id]._total` (see
 * api/runs.py::_generate_summary_metrics) for metric values, and
 * `evaluation.runtime.strategies[id]` for the strategy's name/tags.
 */
import React, { useCallback, useMemo, useState } from 'react'
import {
  Axis,
  BubbleSeries,
  Chart,
  CurveType,
  DARK_THEME,
  LIGHT_THEME,
  LineSeries,
  Position,
  RectAnnotation,
  ScaleType,
  Settings,
  Tooltip,
  TooltipType,
} from '@elastic/charts'
import '@elastic/charts/dist/theme_only_dark.css'
import '@elastic/charts/dist/theme_only_light.css'
import {
  EuiButtonIcon,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFormRow,
  EuiPanel,
  EuiSelect,
  EuiSpacer,
  EuiSwitch,
  EuiText,
  useEuiPaletteColorBlind,
  useEuiTheme,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'

/* -------------------------------------------------------------------------- */
/* Data contract                                                              */
/* -------------------------------------------------------------------------- */

/**
 * Metrics offered in the axis selectors. Relevance metrics report
 * { avg, min, max } across the run's scenarios; latency only reports { avg }
 * (ms), sourced from each search's `took`.
 */
export const METRIC_DEFINITIONS = [
  { key: 'ndcg', label: 'nDCG', direction: 'higher_is_better', kind: 'relevance' },
  { key: 'precision', label: 'Precision', direction: 'higher_is_better', kind: 'relevance' },
  { key: 'recall', label: 'Recall', direction: 'higher_is_better', kind: 'relevance' },
  { key: 'mrr', label: 'MRR', direction: 'higher_is_better', kind: 'relevance' },
  { key: 'latency_avg_ms', label: 'Latency (avg ms)', direction: 'lower_is_better', kind: 'latency' },
]

const LATENCY_METRIC_KEY = 'latency_avg_ms'
const UNGROUPED_FAMILY = 'Untagged'

/* -------------------------------------------------------------------------- */
/* Pure helpers (exported for unit tests)                                     */
/* -------------------------------------------------------------------------- */

/** Sign so that larger is always better on both axes. */
const orient = (direction) => (direction === 'higher_is_better' ? 1 : -1)

/**
 * Build one result per strategy from a run's `summary` + `runtime.strategies`
 * (the shape assembled as `evaluation`/`runWithForensics` elsewhere on this
 * page). Each result looks like:
 *   {
 *     strategyId, strategyName, family, scenarioCount,
 *     metrics: { [metricKey]: { value, rangeLower?, rangeUpper? } }
 *   }
 */
export function buildResultsFromEvaluation(evaluation) {
  const byStrategyId = evaluation?.summary?.strategy_id ?? {}
  const runtimeStrategies = evaluation?.runtime?.strategies ?? {}
  const results = []
  for (const strategyId in byStrategyId) {
    const total = byStrategyId[strategyId]?._total
    if (!total) continue
    const runtime = runtimeStrategies[strategyId]
    const metrics = {}
    for (const def of METRIC_DEFINITIONS) {
      if (def.kind === 'latency') continue
      const m = total.metrics?.[def.key]
      if (!m || !Number.isFinite(m.avg)) continue
      metrics[def.key] = {
        value: m.avg,
        rangeLower: Number.isFinite(m.min) ? m.min : undefined,
        rangeUpper: Number.isFinite(m.max) ? m.max : undefined,
      }
    }
    if (Number.isFinite(total.took?.avg))
      metrics[LATENCY_METRIC_KEY] = { value: total.took.avg }
    const tags = runtime?.tags ?? []
    const scenarioCount = Object.keys(byStrategyId[strategyId]?.by_scenario_id ?? {}).length
    results.push({
      strategyId,
      strategyName: runtime?.name || strategyId,
      family: tags[0] || UNGROUPED_FAMILY,
      scenarioCount: scenarioCount || undefined,
      metrics,
    })
  }
  return results
}

/**
 * Strategy p is dominated if some q is at least as good on both axes and
 * strictly better on at least one.
 */
export function markDominated(points, xDirection, yDirection) {
  const sx = orient(xDirection)
  const sy = orient(yDirection)
  return points.map((p) => {
    const dominated = points.some((q) => {
      if (q === p) return false
      const qx = sx * q.x
      const qy = sy * q.y
      const px = sx * p.x
      const py = sy * p.y
      return qx >= px && qy >= py && (qx > px || qy > py)
    })
    return { ...p, dominated }
  })
}

/** Frontier points sorted by ascending x, ready to draw as a line. */
export function paretoFrontier(points) {
  return points.filter((p) => !p.dominated).sort((a, b) => a.x - b.x)
}

/**
 * Step shape that traces the boundary of the dominated region. When x is
 * lower-is-better, each frontier point holds its y until the next x
 * (step-after). When x is higher-is-better, the next point's y applies
 * from the previous x (step-before). The y direction does not change this.
 */
export function frontierCurve(xDirection) {
  return xDirection === 'lower_is_better' ? CurveType.CURVE_STEP_AFTER : CurveType.CURVE_STEP_BEFORE
}

export function buildPlotPoints(results, xMetric, yMetric, logX, logY) {
  const raw = []
  for (const r of results) {
    const xs = r.metrics[xMetric.key]
    const ys = r.metrics[yMetric.key]
    if (!xs || !ys || !Number.isFinite(xs.value) || !Number.isFinite(ys.value)) continue
    // A log scale cannot place non-positive values.
    if ((logX && xs.value <= 0) || (logY && ys.value <= 0)) continue
    raw.push({
      strategyId: r.strategyId,
      strategyName: r.strategyName,
      family: r.family ?? UNGROUPED_FAMILY,
      scenarioCount: r.scenarioCount,
      x: xs.value,
      y: ys.value,
      xLower: xs.rangeLower,
      xUpper: xs.rangeUpper,
      yLower: ys.rangeLower,
      yUpper: ys.rangeUpper,
    })
  }
  return markDominated(raw, xMetric.direction, yMetric.direction)
}

/** Domain covering points and their ranges, padded; log-safe. */
export function computeDomain(values, log, nonNegative, paddingRatio = 0.08) {
  const finite = values.filter((v) => Number.isFinite(v) && (!log || v > 0))
  if (finite.length === 0) return undefined
  let min = Math.min(...finite)
  let max = Math.max(...finite)
  if (log) {
    const lmin = Math.log10(min)
    const lmax = Math.log10(max)
    const pad = Math.max((lmax - lmin) * paddingRatio, 0.05)
    return { min: 10 ** (lmin - pad), max: 10 ** (lmax + pad) }
  }
  const span = max - min || Math.abs(max) || 1
  min -= span * paddingRatio
  max += span * paddingRatio
  // Latency can't be negative; don't let padding push the axis below 0.
  if (nonNegative) min = Math.max(0, min)
  return { min, max }
}

/* -------------------------------------------------------------------------- */
/* Formatting                                                                 */
/* -------------------------------------------------------------------------- */

const formatMetric = (metric, v) => {
  if (v === undefined || !Number.isFinite(v)) return '–'
  return metric.kind === 'latency' ? `${Math.round(v).toLocaleString()} ms` : v.toFixed(3)
}

const formatTick = (metric) => (v) =>
  metric.kind === 'latency'
    ? `${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
    : Number(v).toFixed(2)

const axisTitle = (metric, axis) => {
  const better =
    axis === 'x'
      ? metric.direction === 'higher_is_better' ? 'better →' : '← better'
      : metric.direction === 'higher_is_better' ? 'better ↑' : 'better ↓'
  return `${metric.label}  (${better})`
}

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const FAMILY_SHAPES = ['circle', 'triangle', 'square', 'diamond', 'x', 'plus']
const FRONTIER_SPEC_ID = 'pareto-frontier'
const POINT_RADIUS = 7

const ChartMetricsTradeoff = ({
  evaluation,
  initialXMetric = LATENCY_METRIC_KEY,
  initialYMetric = 'ndcg',
  height = 420,
  onStrategyClick,
}) => {
  ////  Context  ///////////////////////////////////////////////////////////////

  const { darkMode } = useAppContext()
  const { euiTheme } = useEuiTheme()
  const baseTheme = darkMode ? DARK_THEME : LIGHT_THEME

  ////  Data  ///////////////////////////////////////////////////////////////////

  const results = useMemo(() => buildResultsFromEvaluation(evaluation), [evaluation])

  const metricByKey = useMemo(() => new Map(METRIC_DEFINITIONS.map((m) => [m.key, m])), [])

  // Only offer metrics that at least one strategy has.
  const availableMetrics = useMemo(
    () => METRIC_DEFINITIONS.filter((m) => results.some((r) => r.metrics[m.key] !== undefined)),
    [results],
  )

  ////  State  /////////////////////////////////////////////////////////////////

  const firstAvailable = availableMetrics[0]?.key ?? METRIC_DEFINITIONS[0].key
  const [xKey, setXKey] = useState(metricByKey.has(initialXMetric) ? initialXMetric : firstAvailable)
  const [yKey, setYKey] = useState(metricByKey.has(initialYMetric) ? initialYMetric : firstAvailable)
  const [logLatency, setLogLatency] = useState(false)
  const [showRange, setShowRange] = useState(true)
  const [showFrontier, setShowFrontier] = useState(true)

  const xMetric = metricByKey.get(xKey) ?? METRIC_DEFINITIONS[0]
  const yMetric = metricByKey.get(yKey) ?? METRIC_DEFINITIONS[0]
  const logX = logLatency && xMetric.kind === 'latency'
  const logY = logLatency && yMetric.kind === 'latency'

  const points = useMemo(
    () => buildPlotPoints(results, xMetric, yMetric, logX, logY),
    [results, xMetric, yMetric, logX, logY],
  )
  const frontier = useMemo(() => paretoFrontier(points), [points])

  // Stable family → color/shape assignment, independent of the current filter.
  const families = useMemo(
    () => Array.from(new Set(results.map((r) => r.family ?? UNGROUPED_FAMILY))).sort(),
    [results],
  )
  const palette = useEuiPaletteColorBlind()
  const familyColor = useCallback((f) => palette[families.indexOf(f) % palette.length], [palette, families])
  const familyShape = useCallback((f) => FAMILY_SHAPES[families.indexOf(f) % FAMILY_SHAPES.length], [families])

  const xDomain = useMemo(
    () => computeDomain(
      points.flatMap((p) => [p.x, ...(showRange ? [p.xLower, p.xUpper] : [])].filter((v) => v !== undefined)),
      logX,
      xMetric.kind === 'latency',
    ),
    [points, showRange, logX, xMetric.kind],
  )
  const yDomain = useMemo(
    () => computeDomain(
      points.flatMap((p) => [p.y, ...(showRange ? [p.yLower, p.yUpper] : [])].filter((v) => v !== undefined)),
      logY,
      yMetric.kind === 'latency',
    ),
    [points, showRange, logY, yMetric.kind],
  )

  // Range whiskers (min-max across scenarios) as zero-thickness RectAnnotations,
  // stroked. Split dominated/non-dominated per family so the whiskers dim the
  // same way the point markers do. Elastic Charts has no dedicated error-bar
  // series, hence the annotation trick.
  const whiskersByFamily = useMemo(() => {
    const byFamily = new Map()
    if (!showRange) return byFamily
    for (const p of points) {
      const entry = byFamily.get(p.family) ?? { frontier: [], dominated: [] }
      const bucket = p.dominated ? entry.dominated : entry.frontier
      if (p.xLower !== undefined && p.xUpper !== undefined)
        bucket.push({ coordinates: { x0: p.xLower, x1: p.xUpper, y0: p.y, y1: p.y } })
      if (p.yLower !== undefined && p.yUpper !== undefined)
        bucket.push({ coordinates: { x0: p.x, x1: p.x, y0: p.yLower, y1: p.yUpper } })
      byFamily.set(p.family, entry)
    }
    return byFamily
  }, [points, showRange])

  const pointStyleAccessor = useCallback((datum) => {
    const p = datum.datum
    // Set fill explicitly: DARK_THEME's default bubble fill is the background
    // color (hollow markers), LIGHT_THEME's is the series color.
    const color = familyColor(p.family)
    return {
      shape: familyShape(p.family),
      fill: color,
      stroke: color,
      radius: POINT_RADIUS,
      strokeWidth: 1.5,
      opacity: p.dominated ? 0.35 : 1,
    }
  }, [familyShape, familyColor])

  const handleElementClick = useCallback((elements) => {
    if (!onStrategyClick) return
    const [geometry] = elements[0] || []
    const p = geometry?.datum
    if (p?.strategyId) onStrategyClick(p.strategyId)
  }, [onStrategyClick])

  const tooltip = useCallback(({ values }) => {
    // `values` can hold several series' points near the cursor; use the one
    // actually under the pointer, never the frontier line.
    const candidates = values.filter((v) => v.seriesIdentifier.specId !== FRONTIER_SPEC_ID)
    const hovered = candidates.find((v) => v.isHighlighted) ?? candidates[0]
    const p = hovered?.datum
    if (!p) return null
    return (
      <EuiPanel paddingSize='s' hasShadow={false} hasBorder>
        <EuiText size='xs'>
          <strong>{p.strategyName}</strong>
          <div>
            {p.family} · {p.dominated ? 'dominated' : 'on frontier'}
          </div>
          <div>
            {xMetric.label}: {formatMetric(xMetric, p.x)}
            {p.xLower !== undefined && p.xUpper !== undefined && (
              <> [{formatMetric(xMetric, p.xLower)}, {formatMetric(xMetric, p.xUpper)}]</>
            )}
          </div>
          <div>
            {yMetric.label}: {formatMetric(yMetric, p.y)}
            {p.yLower !== undefined && p.yUpper !== undefined && (
              <> [{formatMetric(yMetric, p.yLower)}, {formatMetric(yMetric, p.yUpper)}]</>
            )}
          </div>
          {p.scenarioCount !== undefined &&
            <div>Scenarios: {p.scenarioCount}</div>
          }
        </EuiText>
      </EuiPanel>
    )
  }, [xMetric, yMetric])

  const metricOptions = availableMetrics.map((m) => ({ value: m.key, text: m.label }))
  const excluded = results.length - points.length

  const themeOverrides = {
    chartMargins: { top: 8, right: 16, bottom: 0, left: 0 },
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  return (
    <div>
      <EuiFlexGroup gutterSize='m' alignItems='flexEnd' wrap responsive={false}>
        <EuiFlexItem grow={false} style={{ minWidth: 200 }}>
          <EuiFormRow label='X axis' display='rowCompressed'>
            <EuiSelect
              compressed
              options={metricOptions}
              value={xKey}
              onChange={(e) => setXKey(e.target.value)}
              aria-label='X axis metric'
            />
          </EuiFormRow>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiButtonIcon
            iconType='merge'
            aria-label='Swap axes'
            title='Swap axes'
            display='base'
            size='s'
            onClick={() => {
              setXKey(yKey)
              setYKey(xKey)
            }}
          />
        </EuiFlexItem>
        <EuiFlexItem grow={false} style={{ minWidth: 200 }}>
          <EuiFormRow label='Y axis' display='rowCompressed'>
            <EuiSelect
              compressed
              options={metricOptions}
              value={yKey}
              onChange={(e) => setYKey(e.target.value)}
              aria-label='Y axis metric'
            />
          </EuiFormRow>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiSwitch compressed label='Log latency axis' checked={logLatency} onChange={(e) => setLogLatency(e.target.checked)} />
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiSwitch compressed label='Range (min–max)' checked={showRange} onChange={(e) => setShowRange(e.target.checked)} />
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiSwitch compressed label='Pareto frontier' checked={showFrontier} onChange={(e) => setShowFrontier(e.target.checked)} />
        </EuiFlexItem>
      </EuiFlexGroup>

      <EuiSpacer size='m' />

      <Chart size={{ height }}>
        <Settings
          baseTheme={baseTheme}
          theme={themeOverrides}
          showLegend
          legendPosition={Position.Right}
          xDomain={xDomain}
          onElementClick={onStrategyClick ? handleElementClick : undefined}
          locale='en-US'
        />
        {/* Tooltip for the point under the pointer; no x-crosshair (an
            x-aligned cursor is meaningless on a scatter). */}
        <Tooltip type={TooltipType.Follow} customTooltip={tooltip} />

        <Axis
          id='x'
          position={Position.Bottom}
          title={axisTitle(xMetric, 'x')}
          tickFormat={formatTick(xMetric)}
          gridLine={{ visible: true }}
        />
        <Axis
          id='y'
          position={Position.Left}
          title={axisTitle(yMetric, 'y')}
          tickFormat={formatTick(yMetric)}
          gridLine={{ visible: true }}
          domain={yDomain}
        />

        {families.map((family) => {
          const whiskers = whiskersByFamily.get(family)
          if (!whiskers) return null
          const color = familyColor(family)
          return (
            <React.Fragment key={`range-${family}`}>
              {whiskers.frontier.length > 0 &&
                <RectAnnotation
                  id={`range-${family}-frontier`}
                  dataValues={whiskers.frontier}
                  hideTooltips
                  zIndex={-1}
                  style={{ stroke: color, strokeWidth: 1.5, fill: color, opacity: 0.7 }}
                />
              }
              {whiskers.dominated.length > 0 &&
                <RectAnnotation
                  id={`range-${family}-dominated`}
                  dataValues={whiskers.dominated}
                  hideTooltips
                  zIndex={-1}
                  style={{ stroke: color, strokeWidth: 1.5, fill: color, opacity: 0.3 }}
                />
              }
            </React.Fragment>
          )
        })}

        {showFrontier && frontier.length > 1 &&
          <LineSeries
            id={FRONTIER_SPEC_ID}
            name='Pareto frontier'
            data={frontier}
            xAccessor='x'
            yAccessors={['y']}
            xScaleType={logX ? ScaleType.Log : ScaleType.Linear}
            yScaleType={logY ? ScaleType.Log : ScaleType.Linear}
            curve={frontierCurve(xMetric.direction)}
            color={euiTheme.colors.textSubdued}
            lineSeriesStyle={{
              line: { strokeWidth: 1.5, dash: [5, 4] },
              point: { visible: 'never' },
            }}
          />
        }

        {families.map((family) => {
          const data = points.filter((p) => p.family === family)
          if (data.length === 0) return null
          return (
            <BubbleSeries
              key={family}
              id={`family-${family}`}
              name={family}
              data={data}
              xAccessor='x'
              yAccessors={['y']}
              xScaleType={logX ? ScaleType.Log : ScaleType.Linear}
              yScaleType={logY ? ScaleType.Log : ScaleType.Linear}
              color={familyColor(family)}
              pointStyleAccessor={pointStyleAccessor}
            />
          )
        })}
      </Chart>

      <EuiSpacer size='s' />
      <EuiText size='xs' color='subdued'>
        {frontier.length} of {points.length} strategies on the frontier. Dimmed points are dominated.
        {excluded > 0 && ` ${excluded} strategies hidden (missing metric${logX || logY ? ' or non-positive value on a log axis' : ''}).`}
      </EuiText>
    </div>
  )
}

export default ChartMetricsTradeoff
