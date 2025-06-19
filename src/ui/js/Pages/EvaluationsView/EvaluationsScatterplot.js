import React, { useEffect, useState } from 'react'
import merge from 'lodash/merge'
import {
  Axis,
  Chart,
  BubbleSeries,
  Position,
  ScaleType,
  Settings,
  Tooltip,
  TooltipType,
  DARK_THEME,
  LIGHT_THEME
} from '@elastic/charts'
import '@elastic/charts/dist/theme_only_dark.css'
import '@elastic/charts/dist/theme_only_light.css'
import {
  EuiFlexGrid,
  EuiFlexItem,
  EuiPanel,
  EuiText
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import utils from '../../utils'

const EvaluationsScatterplot = (props) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { darkMode } = useAppContext()

  ////  Props  /////////////////////////////////////////////////////////////////

  const evaluation = props.evaluation
  const groupBy = props.groupBy || 'strategy_id'
  
  ////  State  /////////////////////////////////////////////////////////////////

  const [data, setData] = useState([])

  /**
   * Create chart data from evaluation results.
   * 
   * Structure of the data object:
   * 
   * [
   *   {
   *     x: FLOAT,  // precision
   *     y: FLOAT,  // recall
   *     z: FLOAT   // (bubble size)
   *   },
   *   ...
   * ]
   */
  useEffect(() => {
    if (!evaluation.results || !groupBy)
      return

    /**
     * Gather metrics by selected grouping.
     * 
     * Structure of the pre-aggregated groups object:
     * 
     * {
     *   key: [ METRIC_VALUE, ... ],
     *   ...
     * }
     */
    const groups = {}
    evaluation.results.forEach((result) => {
      switch (groupBy) {
        case 'strategy_id':
          if (!groups[result.strategy_id])
            groups[result.strategy_id] = { precision: [], recall: [], ndcg: [] }
          break
        case 'strategy_tag':
          runtimeStrategy(result.strategy_id).tags.forEach((tag) => {
            if (!groups[tag])
              groups[tag] = { precision: [], recall: [], ndcg: [] }
          })
          break
        default:
          console.warn(`Not implemented: ${groupBy}`)
          break
      }
      for (const key in groups) {
        result.searches.forEach((search) => {
          groups[key].precision.push(search.metrics.precision)
          groups[key].recall.push(search.metrics.recall)
          groups[key].ndcg.push(search.metrics.ndcg)
        })
      }
    })

    // Aggregate the metrics
    const _data = []
    for (const key in groups) {
      const z = 10 // bubble size
      _data.push({
        recall: utils.average(groups[key].recall),
        precision: utils.average(groups[key].precision),
        ndcg: utils.average(groups[key].ndcg),
        label: key
      })
    }

    setData(prev => {
      // Prevent infinite loop
      if (JSON.stringify(prev) === JSON.stringify(_data))
        return prev
      return _data
    })
    console.debug('[EvaluationsScatterplot state updated]', { _data })
  }, [evaluation, groupBy])

  const runtimeStrategy = (strategyId) => evaluation.runtime?.strategies[strategyId]

  ////  Render  ////////////////////////////////////////////////////////////////

  const baseTheme = {
    axes: {
      gridLine: {
        horizontal: { visible: true },
        vertical: { visible: true },
      }
    },
    bubbleSeriesStyle: {
      point: {
        opacity: 0.6
      },
    },
    markSizeRatio: 20,
  }

  return (
    <Chart size={[400, 400]}>
      <Settings
        onBrushEnd={(e)=> console.log(e)}
        onElementClick={(e)=> console.log(e)}
        pointBuffer={(r) => 20 / r}
        theme={merge({}, darkMode ? DARK_THEME : LIGHT_THEME, baseTheme)}
        xDomain={{ min: 0, max: 1 }}
        yDomain={{ min: 0, max: 1 }}
      />
      <Tooltip
        snap={false}
        type={TooltipType.Follow}
        customTooltip={(d) => {
          const items = []
          const header = [ 'Strategy', 'Precision', 'Recall', 'NDCG' ]
          header.forEach((value, i) => {
            items.push(
              <EuiFlexItem grow={false} key={i}>
                <EuiText size='xs'>
                  <b><small>{value}</small></b>
                </EuiText>
              </EuiFlexItem>
            )
          })
          d.values.forEach((value, i) => {
            if (!value.isHighlighted)
              return
            const keys = [ 'label', 'precision', 'recall', 'ndcg' ]
            keys.forEach((key, i) => {
              const v = value.datum[key]
              items.push(
                <EuiFlexItem>
                  <EuiText size='xs'>
                    {key == 'label' ? runtimeStrategy(v).name : v.toFixed(4)}
                  </EuiText>
                </EuiFlexItem>
              )
            })
          })
          return (
            <EuiPanel paddingSize='s'>
              <EuiFlexGrid columns={4}>
                {items}
              </EuiFlexGrid>
            </EuiPanel>
          )
        }}
      />
      <Axis
        id='x'
        position={Position.Bottom}
        showOverlappingTicks={true}
        showOverlappingLabels={true}
        tickFormat={(d) => Number(d).toFixed(1)}
        tickValues={[...Array(11).keys()].map(i => i / 10)} // 0.0 to 1.0
        title='Recall'
      />
      <Axis
        id='y'
        position={Position.Left}
        showOverlappingTicks={true}
        showOverlappingLabels={true}
        tickFormat={(d) => Number(d).toFixed(1)}
        tickValues={[...Array(11).keys()].map(i => i / 10)} // 0.0 to 1.0
        title='Precision'
      />
      <BubbleSeries
        id='scatter'
        data={data}
        markFormat={(d) => `NDCG: ${Number(d).toFixed(4)}`}
        markSizeAccessor='ndcg'
        xScaleType={ScaleType.Linear}
        yScaleType={ScaleType.Linear}
        xAccessor='recall'
        yAccessors={['precision']}
      />
    </Chart>
  )
}

export default EvaluationsScatterplot