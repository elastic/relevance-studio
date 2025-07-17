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
import { euiPaletteForStatus } from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import utils from '../../utils'

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

  ////  State  /////////////////////////////////////////////////////////////////

  const [data, setData] = useState([])

  /**
   * Configure color bands
   */
  const numBands = 24
  const colorBands = euiPaletteForStatus(numBands).reverse()
  const min = 0.0
  const max = 1.0
  const bands = []
  // Generate non-linear breakpoints using a power curve
  const skew = 0.5
  const breakpoints = Array.from({ length: numBands + 1 }, (_, i) => {
    const t = Math.pow(i / numBands, skew)
    return min + (max - min) * t
  })
  for (let i = 0; i < numBands; i++) {
    bands.push({
      color: colorBands[i],
      start: i === 0 ? -Infinity : breakpoints[i],
      end: i === numBands - 1 ? Infinity : breakpoints[i + 1],
    })
  }

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
    if (!evaluation.results || !xGroupBy || !xSortBy || !yGroupBy || !ySortBy)
      return
    const _data = []
    for (const [yKey, yValue] of Object.entries(evaluation.summary[yGroupBy])) {
      const total = {
        x: 'Average',
        y: yKey,
        value: evaluation.summary[yGroupBy][yKey]._total.metrics[metric].avg,
      }
      _data.push(total)
      for (const [xKey, xValue] of Object.entries(yValue[`by_${xGroupBy}`])) {
        const row = {
          x: xKey,
          y: yKey,
          value: xValue.metrics[metric].avg,
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

    setData(prev => {
      // Prevent infinite loop
      if (JSON.stringify(prev) === JSON.stringify(_data))
        return prev
      return _data
    })
    console.debug('[EvaluationsHeatmap state updated]', { data })
  }, [evaluation, xGroupBy, xSortBy, yGroupBy, ySortBy])

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
          try {
            return runtimeStrategy(label).name
          } catch (e) {
            return label
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