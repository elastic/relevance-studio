/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useState } from 'react'
import {
  EuiAccordion,
  EuiBadge,
  EuiBasicTable,
  EuiButtonEmpty,
  EuiCallOut,
  EuiCodeBlock,
  EuiFieldNumber,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFormRow,
  EuiPanel,
  EuiSelect,
  EuiSpacer,
  EuiSwitch,
  EuiText,
} from '@elastic/eui'
import { VariantsTable } from '../../Layout'
import { useAppContext } from '../../Contexts/AppContext'
import api from '../../api'
import hp from '../../hyperparameters'
import utils from '../../utils'

const METRIC_LABELS = { mrr: 'MRR', ndcg: 'NDCG', precision: 'Precision', recall: 'Recall' }
const fmt = (value, digits = 4) =>
  (value === null || value === undefined) ? '–' : Number(value).toFixed(digits)

/**
 * The expanded row of a strategy in the run summary table.
 *
 * For a strategy that ran several variants, it shows the winner against the
 * baseline, the notices that qualify the result, and a table of the variants
 * with a column per hyperparameter. The table re-ranks under another objective
 * or latency constraint on demand. A re-ranking is exploratory: it uses only
 * tuning scores, and the holdout never decided the run's winner.
 *
 * Every strategy also shows its template.
 */
const StrategyVariants = ({
  workspaceId,
  benchmarkId,
  run,
  strategyId,
  runtimeStrategy,
  optimization,
  summaryStrategy,
  scenarioCounts,
  metrics = [],
  onSelectVariant,
  selectedVariantId,
}) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const runObjective = run?.task?.optimization?.objective || { metric: metrics[0] || 'ndcg', aggregation: 'mean' }
  const runConstraint = run?.task?.optimization?.latency_constraint || null
  const [objective, setObjective] = useState(runObjective)
  const [constraintEnabled, setConstraintEnabled] = useState(Boolean(runConstraint))
  const [constraint, setConstraint] = useState(runConstraint || { stat: 'median', max_ms: '' })
  const [sort, setSort] = useState({ field: 'rank', direction: 'asc' })
  const [pageIndex, setPageIndex] = useState(0)
  const [pageSize, setPageSize] = useState(10)
  const [data, setData] = useState({ items: [], total: 0, hyperparameters: [], ranking: null })
  const [isLoading, setIsLoading] = useState(false)

  const hasVariants = (optimization?.variant_count || 0) > 1
  const effectiveConstraint = constraintEnabled && Number(constraint.max_ms) > 0
    ? { stat: constraint.stat, max_ms: Number(constraint.max_ms) }
    : null
  const isExploratory = objective.metric !== runObjective.metric
    || objective.aggregation !== runObjective.aggregation
    || JSON.stringify(effectiveConstraint) !== JSON.stringify(runConstraint)

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Load a page of variants. Server-side ranking and sorting keep the payload
   * small for searches with hundreds of variants.
   */
  useEffect(() => {
    if (!hasVariants)
      return
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        setIsLoading(true)
        const response = await api.runs_get_variants(workspaceId, benchmarkId, run._id, {
          strategy_id: strategyId,
          size: pageSize,
          page: pageIndex + 1,
          sort: sort.field,
          descending: sort.direction === 'desc',
          objective_metric: objective.metric,
          objective_aggregation: objective.aggregation,
          constraint_stat: effectiveConstraint?.stat,
          constraint_max_ms: effectiveConstraint?.max_ms,
        })
        if (cancelled)
          return
        if (response.status > 299)
          return addToast(utils.toastClientResponse(response))
        setData(response.data)
      } catch (e) {
        if (!cancelled)
          addToast(api.errorToast(e, { title: 'Failed to get variants' }))
      } finally {
        if (!cancelled)
          setIsLoading(false)
      }
    }, 300)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [
    workspaceId, benchmarkId, run?._id, strategyId, hasVariants,
    pageIndex, pageSize, sort.field, sort.direction,
    objective.metric, objective.aggregation,
    effectiveConstraint?.stat, effectiveConstraint?.max_ms,
  ])

  ////  Render  ////////////////////////////////////////////////////////////////

  const notices = (() => {
    const list = hp.optimizationNotices(optimization, run, scenarioCounts)
    // Add the server's warnings that the client rules don't cover
    const known = new Set(list.map((n) => n.text))
    for (const text of summaryStrategy?.warnings || []) {
      const duplicate = /in-sample|judgement coverage|too few|latency constraint/i.test(text)
      if (!known.has(text) && !duplicate)
        list.push({ type: 'server', color: 'warning', text })
    }
    return list
  })()

  const renderNotices = () => notices.map((notice) => (
    <div key={notice.type + notice.text} style={{ marginBottom: '8px' }}>
      <EuiCallOut color={notice.color} iconType={notice.color === 'primary' ? 'iInCircle' : 'help'} size='s' title={notice.text} />
    </div>
  ))

  const renderComparison = () => {
    const basis = optimization.score_basis
    const rows = [
      { id: 'winner', label: 'Winner', tuning: optimization.tuning, holdout: optimization.holdout },
      { id: 'baseline', label: 'Baseline', tuning: optimization.baseline_tuning, holdout: optimization.baseline_holdout },
    ]
    const gain = hp.winnerGain(optimization, runObjective)
    return (
      <>
        <EuiBasicTable
          columns={[
            { field: 'label', name: '', render: (label) => <EuiText size='xs'><b>{label}</b></EuiText> },
            ...metrics.map((metric) => ({
              field: metric,
              name: `${METRIC_LABELS[metric] || metric} ${basis === 'holdout' ? '(holdout)' : '(in-sample)'}`,
              render: (_, row) => {
                const block = basis === 'holdout' ? row.holdout : row.tuning
                const value = block?.metrics?.[metric]?.avg
                return <EuiText size='xs'>{metric === runObjective.metric ? <b>{fmt(value)}</b> : fmt(value)}</EuiText>
              },
            })),
            ...(basis === 'holdout' ? [{
              field: 'tuning',
              name: `${METRIC_LABELS[runObjective.metric] || runObjective.metric} (tuning)`,
              render: (_, row) => <EuiText color='subdued' size='xs'>{fmt(row.tuning?.metrics?.[runObjective.metric]?.avg)}</EuiText>,
            }] : []),
          ]}
          itemId='id'
          items={rows}
          responsiveBreakpoint={false}
        />
        {gain &&
          <EuiText size='xs' style={{ marginTop: '4px' }}>
            <EuiBadge color={gain.delta > 0 ? 'success' : (gain.delta < 0 ? 'danger' : 'hollow')}>
              {gain.delta > 0 ? '+' : ''}{gain.delta.toFixed(4)}
            </EuiBadge>{' '}
            {METRIC_LABELS[runObjective.metric] || runObjective.metric} for the winner over the baseline
            {basis === 'holdout' ? ' on the holdout' : ' (in-sample)'}
          </EuiText>
        }
      </>
    )
  }

  const renderControls = () => (
    <>
      <EuiFlexGroup alignItems='flexEnd' gutterSize='s' responsive={false} wrap>
        <EuiFlexItem grow={false} style={{ width: '150px' }}>
          <EuiFormRow display='rowCompressed' label='Rank by'>
            <EuiSelect
              aria-label='Objective metric'
              compressed
              onChange={(e) => { setObjective((prev) => ({ ...prev, metric: e.target.value })); setPageIndex(0) }}
              options={metrics.map((m) => ({ value: m, text: METRIC_LABELS[m] || m }))}
              value={objective.metric}
            />
          </EuiFormRow>
        </EuiFlexItem>
        <EuiFlexItem grow={false} style={{ width: '130px' }}>
          <EuiFormRow display='rowCompressed' label='Aggregation'>
            <EuiSelect
              aria-label='Objective aggregation'
              compressed
              onChange={(e) => { setObjective((prev) => ({ ...prev, aggregation: e.target.value })); setPageIndex(0) }}
              options={[{ value: 'mean', text: 'Mean' }, { value: 'median', text: 'Median' }]}
              value={objective.aggregation}
            />
          </EuiFormRow>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiFormRow display='rowCompressed' label='Latency limit'>
            <EuiSwitch
              checked={constraintEnabled}
              compressed
              label={<small>Limit</small>}
              onChange={(e) => { setConstraintEnabled(e.target.checked); setPageIndex(0) }}
            />
          </EuiFormRow>
        </EuiFlexItem>
        {constraintEnabled &&
          <>
            <EuiFlexItem grow={false} style={{ width: '100px' }}>
              <EuiFormRow display='rowCompressed' label='Statistic'>
                <EuiSelect
                  aria-label='Latency statistic'
                  compressed
                  onChange={(e) => setConstraint((prev) => ({ ...prev, stat: e.target.value }))}
                  options={[{ value: 'mean', text: 'Mean' }, { value: 'median', text: 'Median' }, { value: 'p90', text: 'p90' }]}
                  value={constraint.stat}
                />
              </EuiFormRow>
            </EuiFlexItem>
            <EuiFlexItem grow={false} style={{ width: '120px' }}>
              <EuiFormRow display='rowCompressed' label='Max (ms)'>
                <EuiFieldNumber
                  aria-label='Maximum latency'
                  compressed
                  min={1}
                  onChange={(e) => setConstraint((prev) => ({ ...prev, max_ms: e.target.value }))}
                  value={constraint.max_ms}
                />
              </EuiFormRow>
            </EuiFlexItem>
          </>
        }
        {isExploratory &&
          <EuiFlexItem grow={false}>
            <EuiButtonEmpty
              iconType='refresh'
              onClick={() => {
                setObjective(runObjective)
                setConstraintEnabled(Boolean(runConstraint))
                setConstraint(runConstraint || { stat: 'median', max_ms: '' })
                setPageIndex(0)
              }}
              size='s'
            >
              Reset to the run's objective
            </EuiButtonEmpty>
          </EuiFlexItem>
        }
      </EuiFlexGroup>
      {isExploratory &&
        <>
          <EuiSpacer size='s' />
          <EuiCallOut color='accent' iconType='beaker' size='s' title='Exploratory ranking'>
            <p>
              This ranking uses tuning scores only, and tuning scores are in-sample. The holdout exists only for the run's
              winner and the baseline, because the run chose its winner under {METRIC_LABELS[runObjective.metric] || runObjective.metric}.
              To confirm another variant, run a new benchmark with that objective.
            </p>
          </EuiCallOut>
        </>
      }
    </>
  )

  const renderTemplate = () => (
    <EuiAccordion buttonContent={<EuiText size='s'>Template</EuiText>} id={`template-${strategyId}`} paddingSize='s'>
      <EuiCodeBlock isCopyable language='json' overflowHeight={400} paddingSize='m' style={{ width: '100%' }}>
        {(() => {
          try {
            return utils.formatJsonWithMustache(runtimeStrategy?.template?.source)
          } catch (e) {
            return runtimeStrategy?.template?.source || ''
          }
        })()}
      </EuiCodeBlock>
    </EuiAccordion>
  )

  return (
    <EuiPanel color='transparent' paddingSize='s' style={{ width: '100%' }}>
      {renderNotices()}
      {hasVariants &&
        <>
          {renderComparison()}
          <EuiSpacer size='m' />
          {renderControls()}
          <EuiSpacer size='m' />
          <VariantsTable
            exploratory={isExploratory}
            hyperparameters={data.hyperparameters?.length ? data.hyperparameters : (runtimeStrategy?._resolved_hyperparameters || [])}
            isLoading={isLoading}
            items={data.items}
            metrics={metrics}
            objective={data.ranking?.objective || objective}
            onPageChange={({ pageIndex: i, pageSize: size }) => { setPageIndex(i); setPageSize(size) }}
            onSelect={onSelectVariant}
            onSortChange={(next) => { setSort(next); setPageIndex(0) }}
            pageIndex={pageIndex}
            pageSize={pageSize}
            selectedId={selectedVariantId}
            serverSide
            sort={sort}
            totalItemCount={data.total}
          />
          <EuiSpacer size='m' />
        </>
      }
      {renderTemplate()}
    </EuiPanel>
  )
}

export default StrategyVariants
