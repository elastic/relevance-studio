import React, { useEffect, useState } from 'react'
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

const EvaluationsHeatmap = (props) => {

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
  const numColorBands = 25
  const colorBands = euiPaletteForStatus(numColorBands).reverse()
  const valueMin = 0.0
  const valueMax = 1.0
  const valueRange = valueMax - valueMin
  const bands = []
  for (let i = 0; i < numColorBands; i++) {
    bands.push({
      color: colorBands[i],
      start: i == 0 ? -Infinity : valueRange / numColorBands * (i),
      end: i == numColorBands - 1 ? Infinity : valueRange / numColorBands * (i + 1)
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

    /**
     * Gather metrics by selected groupings.
     * 
     * Structure of the pre-aggregated groups object:
     * 
     * {
     *   yKey: {
     *     xKey: [ METRIC_VALUE, ... ],
     *     ...
     *   },
     *   ...
     * }
     */
    const groups = {}
    evaluation.results.forEach((result) => {
      let yKeys = []
      switch (yGroupBy) {
        case 'strategy_id':
          yKeys = [result.strategy_id]
          if (!groups[result.strategy_id])
            groups[result.strategy_id] = {}
          break
        case 'strategy_tag':
          yKeys = runtimeStrategy(result.strategy_id).tags
          yKeys.forEach((tag) => {
            if (!groups[tag])
              groups[tag] = {}
          })
          break
        default:
          console.warn(`Not implemented: ${yGroupBy}`)
          return
      }
      result.searches.forEach((search) => {
        switch (xGroupBy) {
          case 'scenario_id': {
            const xKey = search.scenario_id
            yKeys.forEach(yKey => {
              if (!groups[yKey][xKey])
                groups[yKey][xKey] = []
              groups[yKey][xKey].push(search.metrics[metric])
            })
            break
          }
          case 'scenario_tag': {
            const tags = runtimeScenario(search.scenario_id).tags
            yKeys.forEach(yKey => {
              tags.forEach(tag => {
                if (!groups[yKey][tag])
                  groups[yKey][tag] = []
                groups[yKey][tag].push(search.metrics[metric])
              })
            })
            break
          }
          default:
            console.warn(`Not implemented: ${xGroupBy}`)
            return
        }
      })
    })

    // Aggregate the metrics, and create a total _avg column
    const groupsData = []
    const avgRows = []
    for (const y in groups) {
      const yRow = []
      const rowValues = groups[y]
      const xKeys = Object.keys(rowValues)
      let ySum = 0
      let yCount = 0
      for (const x of xKeys) {
        const vals = rowValues[x]
        const avg = utils.average(vals)
        yRow.push({ x, y, value: avg })
        ySum += avg
        yCount++
      }
      const yAvg = ySum / yCount
      avgRows.push({ y, avg: yAvg })
      yRow.unshift({ x: '_avg', y, value: yAvg }) // _avg always comes first
      groupsData.push(...yRow)
    }
    console.warn(groupsData)

    // Y axis order
    const yOrder = avgRows
      .sort((a, b) => ySortBy.order === 'desc' ? b.avg - a.avg : a.avg - b.avg)
      .map(d => d.y)
    const yIndex = Object.fromEntries(yOrder.map((y, i) => [y, i]))

    // X axis order, calculated from group data
    const xSums = {}
    const xCounts = {}
    groupsData.forEach(d => {
      if (d.x === '_avg') return
      if (!xSums[d.x]) {
        xSums[d.x] = 0
        xCounts[d.x] = 0
      }
      xSums[d.x] += d.value
      xCounts[d.x]++
    })
    const xAvgs = Object.keys(xSums).map(x => ({
      x, avg: xSums[x] / xCounts[x]
    }))
    const xOrder = ['_avg', ...xAvgs
      .sort((a, b) =>
        xSortBy.order === 'desc' ? b.avg - a.avg : a.avg - b.avg
      ).map(d => d.x)]
    const xIndex = Object.fromEntries(xOrder.map((x, i) => [x, i]))

    // Final sort
    const orderedData = groupsData.sort((a, b) => {
      if (yIndex[a.y] !== yIndex[b.y])
        return yIndex[a.y] - yIndex[b.y]
      return xIndex[a.x] - xIndex[b.x]
    })

    setData(prev => {
      // Prevent infinite loop
      if (JSON.stringify(prev) === JSON.stringify(orderedData))
        return prev
      return orderedData
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

export default EvaluationsHeatmap