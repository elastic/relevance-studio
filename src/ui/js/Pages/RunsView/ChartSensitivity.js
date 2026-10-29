/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

/**
 * ChartSensitivity
 *
 * Shows how much each hyperparameter matters. For every hyperparameter of a
 * strategy, a small chart plots the mean objective score (tuning, in-sample)
 * at each value, averaged over all the other hyperparameters. A flat line
 * means the hyperparameter barely matters. Hyperparameters sort by spread,
 * the gap between their best and worst mean score.
 *
 * DATA CONTRACT
 * Fed from the run's optimization summary (`runs_get_optimization_summary`):
 * `strategies[].sensitivity[]` with `{ name, kind, spread, points: [[value, mean]] }`.
 */
import { useMemo, useState } from 'react'
import {
  Axis,
  BarSeries,
  Chart,
  CurveType,
  DARK_THEME,
  LIGHT_THEME,
  LineSeries,
  Position,
  ScaleType,
  Settings,
} from '@elastic/charts'
import '@elastic/charts/dist/theme_only_dark.css'
import '@elastic/charts/dist/theme_only_light.css'
import {
  EuiBadge,
  EuiCallOut,
  EuiFlexGrid,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFormRow,
  EuiPanel,
  EuiSelect,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { formatValue } from '../../hyperparameters'

const METRIC_LABELS = { mrr: 'MRR', ndcg: 'NDCG', precision: 'Precision', recall: 'Recall' }

/**
 * Turn a hyperparameter's sensitivity entry into chart data.
 * Numeric hyperparameters plot on a linear x axis. Others plot as categories.
 * Returns `{ kind, data, min, max }` where data is `[{ x, y }]`.
 */
export const sensitivitySeries = (entry) => {
  const points = (entry?.points || []).filter((p) => p[1] !== null && p[1] !== undefined)
  const kind = entry?.kind === 'numeric' ? 'numeric' : 'categorical'
  const data = points.map(([value, mean]) => ({
    x: kind === 'numeric' ? Number(value) : formatValue(value) || String(value),
    y: mean,
  }))
  const ys = data.map((d) => d.y)
  return {
    kind,
    data,
    min: ys.length ? Math.min(...ys) : 0,
    max: ys.length ? Math.max(...ys) : 1,
  }
}

/**
 * The strategies of a summary that ran more than one variant.
 */
export const optimizedStrategies = (summary) =>
  (summary?.strategies || []).filter((s) => (s.variant_count || 0) > 1)

const ChartHyperparameter = ({ entry, objective, darkMode }) => {
  const { kind, data, min, max } = sensitivitySeries(entry)
  const pad = (max - min) * 0.1 || 0.01
  return (
    <EuiPanel hasBorder paddingSize='s'>
      <EuiFlexGroup alignItems='center' gutterSize='s' responsive={false}>
        <EuiFlexItem>
          <EuiText size='s'><b>{entry.name}</b></EuiText>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiBadge color={entry.spread < 0.005 ? 'hollow' : 'primary'}>
            <small>Spread {entry.spread.toFixed(4)}</small>
          </EuiBadge>
        </EuiFlexItem>
      </EuiFlexGroup>
      <Chart size={['100%', 180]}>
        <Settings
          showLegend={false}
          theme={darkMode ? DARK_THEME : LIGHT_THEME}
        />
        <Axis
          id='x'
          position={Position.Bottom}
          tickFormat={(v) => (typeof v === 'number' ? formatValue(v) : String(v))}
        />
        <Axis
          domain={{ min: Math.max(0, min - pad), max: max + pad }}
          id='y'
          position={Position.Left}
          tickFormat={(v) => Number(v).toFixed(3)}
          title={METRIC_LABELS[objective?.metric] || objective?.metric}
        />
        {kind === 'numeric'
          ? (
            <LineSeries
              curve={CurveType.CURVE_MONOTONE_X}
              data={data}
              id={`line-${entry.name}`}
              pointStyleAccessor={() => ({ visible: true, radius: 3 })}
              xAccessor='x'
              xScaleType={ScaleType.Linear}
              yAccessors={['y']}
              yScaleType={ScaleType.Linear}
            />
          )
          : (
            <BarSeries
              data={data}
              id={`bar-${entry.name}`}
              xAccessor='x'
              xScaleType={ScaleType.Ordinal}
              yAccessors={['y']}
              yScaleType={ScaleType.Linear}
            />
          )
        }
      </Chart>
    </EuiPanel>
  )
}

const ChartSensitivity = ({ summary }) => {

  const { darkMode } = useAppContext()
  const strategies = useMemo(() => optimizedStrategies(summary), [summary])
  const [selectedId, setSelectedId] = useState(null)

  if (!strategies.length) {
    return (
      <EuiCallOut color='primary' iconType='iInCircle' size='s' title='No hyperparameter search in this run'>
        <p>The sensitivity of hyperparameters shows for strategies that ran more than one variant.</p>
      </EuiCallOut>
    )
  }

  const strategy = strategies.find((s) => s.strategy_id === selectedId) || strategies[0]
  const sensitivity = strategy.sensitivity || []

  return (
    <div>
      <EuiFlexGroup alignItems='flexEnd' gutterSize='m' responsive={false}>
        <EuiFlexItem grow={false}>
          <EuiText size='s'><b>Hyperparameter sensitivity</b></EuiText>
        </EuiFlexItem>
        {strategies.length > 1 &&
          <EuiFlexItem grow={false} style={{ width: '260px' }}>
            <EuiFormRow display='rowCompressed' label='Strategy'>
              <EuiSelect
                aria-label='Strategy'
                compressed
                onChange={(e) => setSelectedId(e.target.value)}
                options={strategies.map((s) => ({ value: s.strategy_id, text: s.name || s.strategy_id }))}
                value={strategy.strategy_id}
              />
            </EuiFormRow>
          </EuiFlexItem>
        }
      </EuiFlexGroup>
      <EuiText color='subdued' size='xs'>
        <p>
          Mean {METRIC_LABELS[summary.objective?.metric] || summary.objective?.metric} across {strategy.variant_count} variants
          at each value, averaged over the other hyperparameters. The scores come from tuning scenarios, so they are
          in-sample. A flat line means the hyperparameter barely matters.
        </p>
      </EuiText>
      <EuiSpacer size='m' />
      {sensitivity.length === 0
        ? <EuiText color='subdued' size='s'>This strategy has no hyperparameters to compare.</EuiText>
        : (
          <EuiFlexGrid columns={2} gutterSize='m'>
            {sensitivity.map((entry) => (
              <EuiFlexItem key={entry.name}>
                <ChartHyperparameter darkMode={darkMode} entry={entry} objective={summary.objective} />
              </EuiFlexItem>
            ))}
          </EuiFlexGrid>
        )
      }
    </div>
  )
}

export default ChartSensitivity
