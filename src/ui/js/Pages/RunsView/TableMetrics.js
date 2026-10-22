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
  EuiCodeBlock,
  EuiInMemoryTable,
  EuiPanel,
  EuiProgress,
  EuiScreenReaderOnly,
  EuiText,
} from '@elastic/eui'
import { usePageResources } from '../../Contexts/ResourceContext'
import { getHistory } from '../../history'
import utils from '../../utils'

const TableMetrics = ({ evaluation, rowOnHover }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const history = getHistory()
  const { workspace } = usePageResources()

  ////  State  /////////////////////////////////////////////////////////////////

  const [items, setItems] = useState([])
  const [itemsToExpandedRows, setItemIdToExpandedRowMap] = useState({})
  const [sort, setSort] = useState({
    field: 'name',
    direction: 'asc',
  })

  const toggleDetails = (item) => {
    setItemIdToExpandedRowMap(prev => {
      const next = { ...prev }
      next[item.strategy_id] ? delete next[item.strategy_id] : (next[item.strategy_id] = renderDetails(item))
      return next
    })
  }

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
      }
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

  const renderDetails = (item) => {
    return (
      <EuiPanel color='transparent' paddingSize='none'>
        <EuiCodeBlock
          isCopyable
          language='json'
          paddingSize='m'
          overflowHeight={400}
          style={{ width: '100%' }}
        >
          {utils.formatJsonWithMustache(runtimeStrategy(item?.strategy_id)?.template?.source)}
        </EuiCodeBlock>
      </EuiPanel>
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
        const _itemsToExpandedRows = { ...itemsToExpandedRows }
        return (
          <EuiButtonIcon
            onClick={() => toggleDetails(item)}
            aria-label={
              _itemsToExpandedRows[item?.strategy_id] ? 'Collapse' : 'Expand'
            }
            iconType={
              _itemsToExpandedRows[item?.strategy_id] ? 'arrowDown' : 'arrowRight'
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

  return (
    <div className='runs-table-metrics' style={{ height: '390px', overflow: 'auto' }}>
      <EuiInMemoryTable
        allowNeutralSort={false}
        columns={columns}
        itemId='strategy_id'
        itemIdToExpandedRowMap={itemsToExpandedRows}
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
  )
}

export default TableMetrics