/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiButtonIcon,
  EuiInMemoryTable,
  EuiProgress,
  EuiScreenReaderOnly,
  EuiSpacer,
  EuiText,
  EuiToolTip,
} from '@elastic/eui'
import { usePageResources } from '../../Contexts/ResourceContext'
import { getHistory } from '../../history'
import FlyoutVariant from './FlyoutVariant'
import StrategyVariants from './StrategyVariants'
import hp from '../../hyperparameters'

const TableMetrics = ({ evaluation, rowOnHover, optimizationSummary }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const history = getHistory()
  const { workspace, benchmark } = usePageResources()

  ////  State  /////////////////////////////////////////////////////////////////

  const [items, setItems] = useState([])
  const [expandedIds, setExpandedIds] = useState({})
  const [variantInFocus, setVariantInFocus] = useState(null) // { strategyId, variant }
  const [sort, setSort] = useState({
    field: 'name',
    direction: 'asc',
  })

  const toggleDetails = (item) => {
    setExpandedIds(prev => {
      const next = { ...prev }
      next[item.strategy_id] ? delete next[item.strategy_id] : (next[item.strategy_id] = true)
      return next
    })
  }

  const isOptimized = hp.isOptimizedRun(evaluation)
  const objective = evaluation?.task?.optimization?.objective || { metric: 'ndcg', aggregation: 'mean' }
  const taskMetrics = evaluation?.task?.metrics || []

  const runtimeStrategy = (strategyId) => evaluation.runtime?.strategies?.[strategyId]

  const sortPriority = ['ndcg', 'precision', 'recall', 'mrr']
  const metricLabels = {
    ndcg: 'NDCG',
    precision: 'Precision',
    recall: 'Recall',
    mrr: 'MRR',
  }

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Create chart data from evaluation results.
   */
  useEffect(() => {
    // The per-search results now live in a separate store; the summary table
    // is driven by `summary` (on the run doc) plus strategy names/tags from the
    // runtime snapshot (lazy-loaded from forensics), which may arrive after the
    // first render — so gate on `summary` and fall back to the id for the name.
    if (!evaluation?.summary?.strategy_id)
      return
    const rows = []
    for (const _id in evaluation.summary.strategy_id) {
      let row = {
        strategy_id: _id,
        name: runtimeStrategy(_id)?.name || _id,
        tags: runtimeStrategy(_id)?.tags || [],
        metrics: evaluation.summary.strategy_id[_id]._total.metrics,
        unrated_docs: evaluation.summary.strategy_id[_id]._total.unrated_docs,
        took: evaluation.summary.strategy_id[_id]._total.took,
        optimization: evaluation.summary.strategy_id[_id].optimization,
      }
      row.variant_count = row.optimization?.variant_count || 1
      row.gain = hp.winnerGain(row.optimization, objective)?.delta
      row['rated_docs'] = {
        percent: 100 - row.unrated_docs.percent
      }
      rows.push(row)
    }
    setItems(rows)

    // Sort by preferred metric, otherwise by strategy name.
    // Only auto-apply sort if user hasn't changed it yet.
    if (sort.field === 'name') {
      for (const metric of sortPriority) {
        if ((evaluation.task?.metrics || []).includes(metric)) {
          setSort({
            field: `metrics.${metric}.avg`,
            direction: 'desc',
          });
          break;
        }
      }
    }
  }, [evaluation])

  ////  Render  ////////////////////////////////////////////////////////////////

  const scenarioCounts = optimizationSummary?.scenarios

  const summaryStrategy = (strategyId) =>
    (optimizationSummary?.strategies || []).find((s) => s.strategy_id === strategyId)

  const itemIdToExpandedRowMap = {}
  for (const item of items) {
    if (!expandedIds[item.strategy_id])
      continue
    itemIdToExpandedRowMap[item.strategy_id] = (
      <StrategyVariants
        benchmarkId={benchmark?._id}
        metrics={taskMetrics}
        onSelectVariant={(variant) => setVariantInFocus({ strategyId: item.strategy_id, variant })}
        optimization={item.optimization}
        run={evaluation}
        runtimeStrategy={runtimeStrategy(item.strategy_id)}
        scenarioCounts={scenarioCounts}
        selectedVariantId={variantInFocus?.strategyId === item.strategy_id ? variantInFocus.variant.variant_id : undefined}
        strategyId={item.strategy_id}
        summaryStrategy={summaryStrategy(item.strategy_id)}
        workspaceId={workspace?._id}
      />
    )
  }

  /**
   * The basis of the headline scores, shown above the table for runs that
   * optimized hyperparameters.
   */
  const renderBasis = () => {
    if (!isOptimized)
      return null
    const withVariants = items.filter((item) => item.variant_count > 1)
    if (!withVariants.length)
      return null
    const hasHoldout = withVariants.every((item) => item.optimization?.score_basis === 'holdout')
    return (
      <div style={{ marginBottom: '8px' }}>
        {hasHoldout
          ? <EuiBadge color='success'>Scores are on the holdout</EuiBadge>
          : <EuiBadge color='warning'>No holdout: scores are in-sample and optimistic</EuiBadge>
        }
        {' '}
        <EuiText component='span' color='subdued' size='xs'>
          <small>Each strategy shows its winning variant. Expand a row to see every variant.</small>
        </EuiText>
      </div>
    )
  }

  const columns = [
    {
      align: 'left',
      width: '40px',
      isExpander: true,
      name: (
        <EuiScreenReaderOnly>
          <span>Expand row</span>
        </EuiScreenReaderOnly>
      ),
      mobileOptions: { header: false },
      render: (item) => {
        return (
          <EuiButtonIcon
            onClick={() => toggleDetails(item)}
            aria-label={
              expandedIds[item?.strategy_id] ? 'Collapse' : 'Expand'
            }
            iconType={
              expandedIds[item?.strategy_id] ? 'arrowDown' : 'arrowRight'
            }
          />
        )
      },
    },
    {
      field: 'name',
      name: 'Strategy',
      sortable: true,
      render: (name, item) => item?.name
    },
    {
      field: 'tags',
      name: 'Tags',
      width: '100px',
      render: (name, item) => {
        const tags = []
        for (var i in item?.tags)
          tags.push(
            <EuiBadge color='hollow' key={item.tags[i]}>
              {item.tags[i]}
            </EuiBadge>
          )
        return tags
      },
    },
  ]
  if (isOptimized) {
    columns.push({
      field: 'variant_count',
      name: 'Variants',
      sortable: true,
      width: '80px',
      render: (count) => <EuiText size='s'>{count}</EuiText>,
    })
  }
  for (const metric of sortPriority) {
    if ((evaluation.task?.metrics || []).includes(metric)) {
      // Highest average across strategies for this metric, so that
      // strategy's value can be bolded (ties all bold too, via ===).
      const bestAvg = items.reduce((best, item) => {
        const avg = item?.metrics?.[metric]?.avg
        return typeof avg === 'number' && (best === undefined || avg > best) ? avg : best
      }, undefined)
      columns.push({
        field: `metrics.${metric}.avg`,
        name: (
          <>
            {metricLabels[metric]} <EuiText component='span' size='xs'><small>(avg)</small></EuiText>
          </>
        ),
        sortable: true,
        style: { width: '100px' },
        render: (name, item) => {
          const avg = item?.metrics?.[metric]?.avg
          const isBest = typeof avg === 'number' && avg === bestAvg
          return (
            <div style={{ position: 'relative', width: '100%' }}>
              {avg === undefined
                ? <EuiText size='s'>-</EuiText>
                // `EuiProgress` resets font-weight on its internal data
                // wrapper (see .euiProgress__data), so bolding the outer
                // element here wouldn't survive that reset — it has to be
                // set via `labelProps`, which lands as an inline style
                // directly on the label `<div>`, taking precedence over it.
                : <EuiProgress
                  color='vis0'
                  label={avg ? avg.toFixed(4) : '-'}
                  labelProps={{ style: { fontWeight: isBest ? 'bold' : undefined } }}
                  max={1}
                  size='s'
                  value={avg}
                />
              }
            </div>
          )
        }
      })
    }
  }
  if (isOptimized) {
    columns.push({
      field: 'gain',
      name: (
        <EuiToolTip content={`Gain of the winner over the baseline for ${objective.metric}, on the holdout when the run has one.`}>
          <span>Gain</span>
        </EuiToolTip>
      ),
      sortable: true,
      width: '90px',
      render: (gain, item) => {
        if (item.variant_count <= 1 || gain === undefined || gain === null)
          return <EuiText color='subdued' size='s'>-</EuiText>
        return (
          <EuiBadge color={gain > 0 ? 'success' : (gain < 0 ? 'danger' : 'hollow')}>
            {gain > 0 ? '+' : ''}{gain.toFixed(4)}
          </EuiBadge>
        )
      },
    })
  }
  columns.push({
    field: 'rated_docs.percent',
    name: (
      <>
        Rated docs
      </>
    ),
    sortable: true,
    style: { width: '100px' },
    render: (name, item) => (
      <div style={{ position: 'relative', width: '100%' }}>
        <EuiProgress
          color='vis0'
          label={item?.rated_docs?.percent?.toFixed(0) + '%'}
          max={1}
          size='s'
          value={item?.rated_docs?.percent / 100.0}
        />
      </div>
    )
  })
  {
    // Lowest average latency across strategies (lower is better), so that
    // strategy's value can be bolded (ties all bold too, via ===). A
    // strategy with no latency value is never a candidate and never bolded.
    const bestTook = items.reduce((best, item) => {
      const avg = item?.took?.avg
      return typeof avg === 'number' && (best === undefined || avg < best) ? avg : best
    }, undefined)
    columns.push({
      field: 'took.avg',
      name: 'Latency',
      sortable: true,
      style: { width: '100px' },
      render: (name, item) => {
        const avg = item?.took?.avg
        const isBest = typeof avg === 'number' && avg === bestTook
        return (
          <EuiText size='s' style={{ fontWeight: isBest ? 'bold' : undefined }}>
            {typeof avg === 'number'
              ? `${Math.round(avg).toLocaleString('en-US')}ms`
              : '-'}
          </EuiText>
        )
      }
    })
  }
  columns.push({
    name: 'Actions',
    actions: [
      {
        color: 'primary',
        description: 'Edit current strategy',
        icon: 'editorLink',
        isPrimary: true,
        name: 'Edit',
        onClick: (item) => {
          history.push({ pathname: `/workspaces/${workspace._id}/strategies/${item?.strategy_id}` })
        },
        type: 'icon'
      },
    ],
  })

  const focusedRuntime = variantInFocus ? runtimeStrategy(variantInFocus.strategyId) : null

  return (
    <>
    {renderBasis()}
    {variantInFocus &&
      <FlyoutVariant
        benchmarkId={benchmark?._id}
        metrics={taskMetrics}
        objective={objective}
        onClose={() => setVariantInFocus(null)}
        runId={evaluation._id}
        runtimeStrategy={focusedRuntime}
        strategyId={variantInFocus.strategyId}
        variant={variantInFocus.variant}
        workspaceId={workspace?._id}
      />
    }
    <div className='runs-table-metrics' style={{ height: Object.keys(expandedIds).length ? '75vh' : '390px', overflow: 'auto' }}>
      <EuiInMemoryTable
        allowNeutralSort={false}
        columns={columns}
        itemId='strategy_id'
        itemIdToExpandedRowMap={itemIdToExpandedRowMap}
        items={items}
        onTableChange={({ sort: newSort }) => {
          if (newSort) setSort(newSort)
        }}
        pagination={false}
        rowProps={(item) => ({
          onMouseEnter: () => rowOnHover(item.strategy_id),
          onMouseLeave: () => rowOnHover(null),
        })}
        search={{
          box: {
            incremental: true,
            schema: true,
          },
          filters: [
            {
              autoSortOptions: false,
              field: 'tags',
              multiSelect: 'or',
              name: 'Tags',
              options: Array.from(new Set(items.flatMap(item => item?.tags || []))).map(tag => ({ value: tag })),
              type: 'field_value_selection',
            },
          ]
        }}
        sorting={{
          sort: sort
        }}
        tableLayout='auto'
      />
    </div>
    </>
  )
}

export default TableMetrics