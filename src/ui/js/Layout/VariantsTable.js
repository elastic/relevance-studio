/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useMemo, useState } from 'react'
import { EuiBadge, EuiBasicTable, EuiLink, EuiText, EuiToolTip } from '@elastic/eui'
import { formatValue, objectiveScore } from '../hyperparameters'

const METRIC_LABELS = { mrr: 'MRR', ndcg: 'NDCG', precision: 'Precision', recall: 'Recall' }

const fmt = (value, digits = 4) =>
  (value === null || value === undefined) ? '–' : Number(value).toFixed(digits)

/**
 * The value a column sorts on, for local sorting. Mirrors the server's
 * `sort` keys: rank, took, coverage, hp:<name> and metric:<name>.
 */
export const sortValue = (item, key) => {
  const tuning = item.aggregates?.tuning
  if (key === 'rank') return item.rank
  if (key === 'took') return tuning?.took?.median
  if (key === 'coverage') return tuning?.coverage
  if (key.startsWith('hp:')) return item.values?.[key.slice(3)]
  if (key.startsWith('metric:')) return tuning?.metrics?.[key.slice(7)]?.avg
  return undefined
}

export const sortVariants = (items, key, descending) => {
  const dir = descending ? -1 : 1
  return [...items].sort((a, b) => {
    const x = sortValue(a, key)
    const y = sortValue(b, key)
    if (x === undefined || x === null) return 1
    if (y === undefined || y === null) return -1
    if (typeof x === 'string' || typeof y === 'string')
      return dir * String(x).localeCompare(String(y))
    return dir * (x - y)
  })
}

/**
 * A table of the hyperparameter variants of one strategy: one column per
 * hyperparameter, the tuning scores, the holdout score where it exists,
 * latency, and judgement coverage.
 *
 * Sorting and paging happen locally unless `serverSide` is set. Then the
 * parent owns them through `sort`, `onSortChange`, `pageIndex`, `pageSize`,
 * `totalItemCount` and `onPageChange`.
 */
const VariantsTable = ({
  items,
  hyperparameters = [],
  metrics = [],
  objective = { metric: 'ndcg', aggregation: 'mean' },
  exploratory = false,
  isLoading = false,
  onSelect,
  selectedId,
  serverSide = false,
  sort,
  onSortChange,
  pageIndex = 0,
  pageSize = 10,
  totalItemCount,
  onPageChange,
}) => {
  const [localSort, setLocalSort] = useState({ field: 'rank', direction: 'asc' })
  const activeSort = serverSide ? (sort || { field: 'rank', direction: 'asc' }) : localSort
  const [localPage, setLocalPage] = useState({ pageIndex: 0, pageSize })

  const sorted = useMemo(
    () => serverSide ? items : sortVariants(items, activeSort.field, activeSort.direction === 'desc'),
    [items, serverSide, activeSort.field, activeSort.direction]
  )
  const page = serverSide ? { pageIndex, pageSize } : localPage
  const shown = serverSide ? sorted : sorted.slice(page.pageIndex * page.pageSize, (page.pageIndex + 1) * page.pageSize)
  const total = serverSide ? (totalItemCount ?? items.length) : sorted.length

  const hasHoldout = items.some((item) => item.aggregates?.holdout)
  const objectiveLabel = METRIC_LABELS[objective.metric] || objective.metric

  const columns = [
    {
      field: 'rank',
      name: '#',
      sortable: true,
      width: '50px',
      render: (rank) => <EuiText size='xs'>{rank}</EuiText>,
    },
    {
      field: 'variant_id',
      name: 'Variant',
      width: '170px',
      render: (id, item) => (
        <div>
          <EuiLink onClick={() => onSelect?.(item)}>
            <code style={{ fontSize: '12px' }}>{id.slice(0, 8)}</code>
          </EuiLink>{' '}
          {item.is_baseline && <EuiBadge color='hollow'><small>Baseline</small></EuiBadge>}
          {item.is_winner && !exploratory && <EuiBadge color='success'><small>Winner</small></EuiBadge>}
          {exploratory && item.is_run_winner && <EuiBadge color='success'><small>Run winner</small></EuiBadge>}
          {exploratory && item.is_winner && !item.is_run_winner && <EuiBadge color='accent'><small>Top</small></EuiBadge>}
          {item.violates_constraint &&
            <EuiToolTip content='Too slow for the latency constraint, so it can’t win.'>
              <EuiBadge color='warning'><small>Slow</small></EuiBadge>
            </EuiToolTip>
          }
        </div>
      ),
    },
    ...hyperparameters.map((hp) => ({
      field: `hp:${hp.name}`,
      name: hp.name,
      sortable: true,
      render: (_, item) => <EuiText size='xs'>{formatValue(item.values?.[hp.name]) || '–'}</EuiText>,
    })),
    ...metrics.map((metric) => ({
      field: `metric:${metric}`,
      name: metric === objective.metric ? `${METRIC_LABELS[metric] || metric} (objective)` : (METRIC_LABELS[metric] || metric),
      sortable: true,
      render: (_, item) => {
        const value = item.aggregates?.tuning?.metrics?.[metric]?.avg
        const text = fmt(value)
        return <EuiText size='xs'>{metric === objective.metric ? <b>{text}</b> : text}</EuiText>
      },
    })),
    ...(hasHoldout ? [{
      field: 'holdout',
      name: `Holdout ${objectiveLabel}`,
      render: (_, item) => {
        const holdout = item.aggregates?.holdout
        if (!holdout)
          return <EuiText color='subdued' size='xs'>–</EuiText>
        return <EuiText size='xs'><b>{fmt(objectiveScore(holdout, objective))}</b></EuiText>
      },
    }] : []),
    {
      field: 'took',
      name: 'Latency (median)',
      sortable: true,
      render: (_, item) => {
        const took = item.aggregates?.tuning?.took?.median
        return <EuiText size='xs'>{took === null || took === undefined ? '–' : `${Math.round(took)} ms`}</EuiText>
      },
    },
    {
      field: 'coverage',
      name: 'Coverage',
      sortable: true,
      render: (_, item) => {
        const coverage = item.aggregates?.tuning?.coverage
        return <EuiText size='xs'>{coverage === null || coverage === undefined ? '–' : `${Math.round(coverage * 100)}%`}</EuiText>
      },
    },
  ]

  return (
    <EuiBasicTable
      columns={columns}
      itemId='variant_id'
      items={shown}
      loading={isLoading}
      onChange={({ page: nextPage, sort: nextSort }) => {
        if (nextSort) {
          if (serverSide) onSortChange?.(nextSort)
          else {
            setLocalSort(nextSort)
            setLocalPage((prev) => ({ ...prev, pageIndex: 0 }))
          }
        }
        if (nextPage) {
          if (serverSide) onPageChange?.(nextPage)
          else setLocalPage(nextPage)
        }
      }}
      pagination={{
        pageIndex: page.pageIndex,
        pageSize: page.pageSize,
        pageSizeOptions: [10, 25, 50],
        totalItemCount: total,
      }}
      responsiveBreakpoint={false}
      rowProps={(item) => ({
        style: item.variant_id === selectedId ? { backgroundColor: 'rgba(0, 119, 204, 0.08)' } : undefined,
      })}
      sorting={{ sort: { field: activeSort.field, direction: activeSort.direction } }}
      tableLayout='auto'
    />
  )
}

export default VariantsTable
