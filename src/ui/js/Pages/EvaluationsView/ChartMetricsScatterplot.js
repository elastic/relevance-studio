import { useEffect, useState } from 'react'
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

const ChartMetricsScatterplot = ({ evaluation, groupBy = 'strategy_id', strategyInFocus }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { darkMode } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [data, setData] = useState([])

  /**
   * Create chart data from evaluation results.
   */
  useEffect(() => {
    if (!evaluation.results || !groupBy)
      return
    const _data = []
    for (const key in evaluation.summary[groupBy]) {
      const row = {
        label: key,
        ndcg: evaluation.summary[groupBy][key]._total.metrics.ndcg.avg,
        precision: evaluation.summary[groupBy][key]._total.metrics.precision.avg,
        recall: evaluation.summary[groupBy][key]._total.metrics.recall.avg,
      }
      _data.push(row)
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
      axisTitle: {
        fontWeight: 500,
      },
      gridLine: {
        horizontal: { visible: true },
        vertical: { visible: true },
      }
    },
    bubbleSeriesStyle: {
      point: {
        fill: darkMode ? '#48EFCF' : '#16C5C0',
        strokeWidth: 0
      },
    },
    markSizeRatio: 20,
  }

  return (
    <EuiPanel hasBorder={false} hasShadow={false} paddingSize='s'>
      <Chart size={[350, 350]}>
        <Settings
          onBrushEnd={(e) => console.log(e)}
          onElementClick={(e) => console.log(e)}
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
            const header = ['Strategy', 'Precision', 'Recall', 'NDCG']
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
              const keys = ['label', 'precision', 'recall', 'ndcg']
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
          ticks={11}
          tickFormat={(d) => Number(d).toFixed(1)}
          tickValues={[...Array(11).keys()].map(i => i / 10)} // 0.0 to 1.0
          title='Recall'
        />
        <Axis
          id='y'
          position={Position.Left}
          showOverlappingTicks={true}
          showOverlappingLabels={true}
          ticks={11}
          tickFormat={(d) => Number(d).toFixed(1)}
          tickValues={[...Array(11).keys()].map(i => i / 10)} // 0.0 to 1.0
          title='Precision'
        />
        <BubbleSeries
          id='scatter'
          data={data}
          markFormat={(d) => `NDCG: ${Number(d).toFixed(4)}`}
          markSizeAccessor='ndcg'
          pointStyleAccessor={(d) => {
            if (!strategyInFocus)
              return { opacity: 0.67 }
            if (strategyInFocus == d.datum.label)
              return { opacity: 1.0 }
            return { opacity: 0.15 }
          }}
          xScaleType={ScaleType.Linear}
          yScaleType={ScaleType.Linear}
          xAccessor='recall'
          yAccessors={['precision']}
        />
      </Chart>
    </EuiPanel>
  )
}

export default ChartMetricsScatterplot