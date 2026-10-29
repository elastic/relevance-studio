/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useState } from 'react'
import merge from 'lodash/merge'
import {
  Chart,
  Heatmap,
  Settings,
  DARK_THEME,
  LIGHT_THEME
} from '@elastic/charts'
import '@elastic/charts/dist/theme_only_dark.css'
import '@elastic/charts/dist/theme_only_light.css'
import { euiPaletteColorBlind } from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'

/**
 * Build the heatmap override of one variant from its stored results (one per
 * scenario). The heatmap shows each strategy's winner by default. An override
 * shows another variant of a strategy instead, with every other strategy
 * unchanged.
 *
 * Returns `{ strategyId, variantId, byScenario: { scenario_id: { metric: value } },
 * avg: { metric: mean } }`.
 */
export const buildVariantOverride = (strategyId, variantId, results) => {
  const byScenario = {}
  const sums = {}
  const counts = {}
  for (const result of results || []) {
    byScenario[result.scenario_id] = result.metrics || {}
    for (const [metric, value] of Object.entries(result.metrics || {})) {
      if (value === null || value === undefined)
        continue
      sums[metric] = (sums[metric] || 0) + value
      counts[metric] = (counts[metric] || 0) + 1
    }
  }
  const avg = {}
  for (const metric of Object.keys(sums))
    avg[metric] = sums[metric] / counts[metric]
  return { strategyId, variantId, byScenario, avg }
}

const ChartMetricsHeatmap = (props) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { darkMode } = useAppContext()

  ////  Props  /////////////////////////////////////////////////////////////////

  const evaluation = props.evaluation
  const metric = props.metric || 'ndcg'
  const xGroupBy = props.xGroupBy || 'scenario_id'
  const xSortBy = props.xSort || { by: 'value', order: 'desc' }
  const yGroupBy = props.yGroupBy || 'strategy_id'
  const ySortBy = props.ySort || { by: 'value', order: 'desc' }
  const variantOverride = props.variantOverride || null

  ////  State  /////////////////////////////////////////////////////////////////

  const [data, setData] = useState([])
  const [dataRange, setDataRange] = useState({ min: 0, max: 1 })

  /**
   * Generate a monochromatic palette using EUI's vis0 color at varying
   * opacities. This naturally adapts to dark and light mode since the
   * background shows through at low values, and vis0 at full opacity
   * is the most intense color for the highest values.
   */
  const numBands = 24
  const vis0 = euiPaletteColorBlind()[0]
  const vis0r = parseInt(vis0.slice(1, 3), 16)
  const vis0g = parseInt(vis0.slice(3, 5), 16)
  const vis0b = parseInt(vis0.slice(5, 7), 16)

  const generateMonoPalette = (n) => {
    return Array.from({ length: n }, (_, i) => {
      // Cubic curve so only the highest values earn full vis0 intensity.
      const t = Math.pow(i / (n - 1), 3)
      const alpha = 0.05 + t * 0.95
      return `rgba(${vis0r}, ${vis0g}, ${vis0b}, ${alpha.toFixed(3)})`
    })
  }
  const colorBands = generateMonoPalette(numBands)
  const range = dataRange.max - dataRange.min || 1
  const bands = colorBands.map((color, i) => ({
    color,
    start: i === 0 ? -Infinity : dataRange.min + (range * i / numBands),
    end: i === numBands - 1 ? Infinity : dataRange.min + (range * (i + 1) / numBands),
  }))

  const runtimeScenario = (scenarioId) => evaluation.runtime?.scenarios?.[scenarioId]
  const runtimeStrategy = (strategyId) => evaluation.runtime?.strategies?.[strategyId]

  /**
   * Create chart data from evaluation results.
   * 
   * Structure of the data object:
   * 
   * [
   *   {
   *     x: STRING,       // scenario_id or scenario tag
   *     y: STRING,       // strategy_id or strategy tag
   *     value: FLOAT     // metric value (or average for aggregates like tags)
   *   },
   *   ...
   * ]
   */
  useEffect(() => {
    // Driven entirely by `summary` (on the run doc); the per-search results now
    // live in a separate store and are not needed here.
    if (!evaluation?.summary || !xGroupBy || !xSortBy || !yGroupBy || !ySortBy)
      return
    const _data = []
    const summary = { ...evaluation.summary }
    for (const [yKey, yValue] of Object.entries(summary[yGroupBy])) {
      // Another variant of this strategy replaces its winner
      const override = (variantOverride && yGroupBy === 'strategy_id' && yKey === variantOverride.strategyId)
        ? variantOverride
        : null
      const total = {
        x: 'Average',
        y: yKey,
        value: override
          ? override.avg?.[metric]
          : summary?.[yGroupBy]?.[yKey]?._total?.metrics?.[metric]?.avg,
      }
      _data.push(total)
      if (override && xGroupBy === 'scenario_id') {
        for (const [scenarioId, metrics] of Object.entries(override.byScenario)) {
          if (metrics?.[metric] === undefined || metrics?.[metric] === null)
            continue
          _data.push({ x: scenarioId, y: yKey, value: metrics[metric] })
        }
        continue
      }
      for (const [xKey, xValue] of Object.entries(yValue[`by_${xGroupBy}`])) {
        // In rare cases it's possible for scenarios without judgements to be
        // included in evaluations. There won't be metrics in those cases.
        if (xValue?.metrics[metric] === undefined)
          continue
        const row = {
          x: xKey,
          y: yKey,
          value: xValue?.metrics?.[metric]?.avg,
        }
        _data.push(row)
      }
    }

    // Sort by overall average value. First, group rows by yKey
    const grouped = {}
    for (const row of _data) {
      if (!grouped[row.y])
        grouped[row.y] = []
      grouped[row.y].push(row)
    }

    // Then, sort group keys by the value of their 'Average' row
    const sortedYKeys = Object.entries(grouped)
      .sort(([, aRows], [, bRows]) => {
        const aAvg = aRows.find(r => r.x === 'Average')?.value ?? -Infinity
        const bAvg = bRows.find(r => r.x === 'Average')?.value ?? -Infinity
        return bAvg - aAvg // descending
      })
      .map(([yKey]) => yKey)

    // Finally, rebuild _data in the new order
    const sortedData = []
    for (const yKey of sortedYKeys) {
      sortedData.push(...grouped[yKey])
    }
    _data.length = 0
    _data.push(...sortedData)

    // Compute data range for relative color scaling
    const values = _data.map(d => d.value).filter(v => v !== undefined && v !== null)
    if (values.length > 0) {
      setDataRange({ min: Math.min(...values), max: Math.max(...values) })
    }

    setData(prev => {
      // Prevent infinite loop
      if (JSON.stringify(prev) === JSON.stringify(_data))
        return prev
      return _data
    })
  }, [evaluation, xGroupBy, xSortBy, yGroupBy, ySortBy, metric, variantOverride])

  ////  Render  ////////////////////////////////////////////////////////////////

  const baseTheme = {
    heatmap: {
      grid: {
        stroke: {
          width: 0,
        },
      },
      cell: {
        maxWidth: 'fill',
        label: {
          minFontSize: 0,
          maxFontSize: 12,
          visible: true,
          useGlobalMinFontSize: true,
        },
        border: {
          stroke: 'transparent',
          strokeWidth: 1,
        },
      },
      xAxisLabel: { visible: true },
      yAxisLabel: { visible: true },
    },
  }

  return (
    <Chart size={['100%', 400]}>
      <Settings
        brushAxis='both'
        legendPosition='right'
        onBrushEnd={(e) => console.log(e)}
        onElementClick={(e) => console.log(e)}
        showLegend={false}
        theme={merge({}, darkMode ? DARK_THEME : LIGHT_THEME, baseTheme)}
      />
      <Heatmap
        id='heatmap'
        colorScale={{ type: 'bands', bands: bands }}
        data={data}
        valueAccessor={(d) => d['value']}
        valueFormatter={(value) => value.toFixed(4)}
        xAxisLabelFormatter={(label) => {
          if (label == '_avg')
            return 'Average'
          try {
            return runtimeScenario(label).name
          } catch (e) {
            return label
          }
        }}
        xAxisTitle={'Scenario'}
        xAccessor={(d) => d['x']}
        yAccessor={(d) => d['y']}
        yAxisLabelFormatter={(label) => {
          const suffix = (variantOverride && label === variantOverride.strategyId)
            ? ` [variant ${variantOverride.variantId.slice(0, 8)}]`
            : ''
          try {
            return runtimeStrategy(label).name + suffix
          } catch (e) {
            return label + suffix
          }
        }}
        yAxisTitle={'Strategy'}
        xSortPredicate={'dataIndex'}
        ySortPredicate={'dataIndex'}
      />
    </Chart>
  )
}

export default ChartMetricsHeatmap