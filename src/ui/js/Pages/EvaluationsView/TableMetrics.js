import React, { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiInMemoryTable,
  EuiProgress,
  EuiText,
  euiPaletteForStatus
} from '@elastic/eui'
import utils from '../../utils'

const TableMetrics = ({ evaluation, rowOnHover }) => {

  const [items, setItems] = useState([])

  /**
   * Configure color bands
   */
  const numBands = 25
  const colors = euiPaletteForStatus(numBands).reverse()
  const min = 0.0
  const max = 1.0
  const step = (max - min) / numBands
  const bands = colors.map((color, i) => ({
    color,
    start: i === 0 ? -Infinity : min + step * i,
    end: i === numBands - 1 ? Infinity : min + step * (i + 1),
  }))
  const getColorBand = (value) => {
    return bands.find(b => value >= b.start && value < b.end)?.color || colors[colors.length - 1]
  }


  ////  Render  ////////////////////////////////////////////////////////////////

  const runtimeStrategy = (strategyId) => evaluation.runtime?.strategies[strategyId]

  /**
   * Create chart data from evaluation results.
   */
  useEffect(() => {
    if (!evaluation.results)
      return
    const dataByStrategy = {}
    evaluation.results.forEach((result) => {
      const strategy_id = result.strategy_id
      if (!dataByStrategy[strategy_id])
        dataByStrategy[strategy_id] = {}
      result.searches.forEach((search) => {
        const scenario_id = search.scenario_id
        if (!dataByStrategy[strategy_id][scenario_id])
          dataByStrategy[strategy_id][scenario_id] = search.metrics
      })
    })
    const rows = []
    for (const strategy_id in dataByStrategy) {
      const metricsAvg = {}
      for (const scenario_id in dataByStrategy[strategy_id]) {
        for (const metric in dataByStrategy[strategy_id][scenario_id]) {
          if (metricsAvg[metric] === undefined)
            metricsAvg[metric] = []
          metricsAvg[metric].push(dataByStrategy[strategy_id][scenario_id][metric])
        }
      }
      const row = {
        strategy_id: strategy_id,
        name: runtimeStrategy(strategy_id).name,
        tags: runtimeStrategy(strategy_id).tags,
        metrics: {}
      }
      for (const metric in metricsAvg)
        row.metrics[metric] = utils.average(metricsAvg[metric])
      rows.push(row)
    }
    console.warn(rows)
    setItems(rows)
  }, [evaluation])

  const columns = [
    {
      field: 'name',
      name: 'Strategy',
      sortable: true,
      render: (name, item) => item.name
    },
    {
      field: 'tags',
      name: 'Tags',
      width: '100px',
      render: (name, item) => {
        const tags = []
        for (var i in item.tags)
          tags.push(
            <EuiBadge color='hollow' key={item.tags[i]}>
              {item.tags[i]}
            </EuiBadge>
          )
        return tags
      },
    },
  ]
  if ((evaluation.task?.metrics || []).includes('ndcg')) {
    columns.push({
      field: 'metrics.ndcg',
      name: (
        <>
          NDCG <EuiText component='span' size='xs'><small>(avg)</small></EuiText>
        </>
      ),
      sortable: true,
      style: { width: '100px' },
      render: (name, item) => (
        <div style={{ position: 'relative', width: '100%' }}>
          <EuiProgress
            color={getColorBand(item.metrics.ndcg)}
            label={item.metrics.ndcg ? item.metrics.ndcg.toFixed(4) : '-'}
            max={1}
            size='s'
            value={item.metrics.ndcg}
          />
        </div>
      )
    })
  }
  if ((evaluation.task?.metrics || []).includes('precision')) {
    columns.push({
      field: 'metrics.precision',
      name: (
        <>
          Precision <EuiText component='span' size='xs'><small>(avg)</small></EuiText>
        </>
      ),
      sortable: true,
      style: { width: '100px' },
      render: (name, item) => (
        <div style={{ position: 'relative', width: '100%' }}>
          <EuiProgress
            color={getColorBand(item.metrics.precision)}
            label={item.metrics.precision ? item.metrics.precision.toFixed(4) : '-'}
            max={1}
            size='s'
            value={item.metrics.precision}
          />
        </div>
      )
    })
  }
  if ((evaluation.task?.metrics || []).includes('recall')) {
    columns.push({
      field: 'metrics.recall',
      name: (
        <>
          Recall <EuiText component='span' size='xs'><small>(avg)</small></EuiText>
        </>
      ),
      sortable: true,
      style: { width: '100px' },
      render: (name, item) => (
        <div style={{ position: 'relative', width: '100%' }}>
          <EuiProgress
            color={getColorBand(item.metrics.recall)}
            label={item.metrics.recall ? item.metrics.recall.toFixed(4) : '-'}
            max={1}
            size='s'
            value={item.metrics.recall}
          />
        </div>
      )
    })
  }

  // Sort by preferred metric, otherwise by strategy name
  let sort = {
    field: 'name',
    direction: 'asc',
  }
  const sortPriority = ['ndcg', 'precision', 'recall']
  for (const i in sortPriority) {
    if ((evaluation.task?.metrics || []).includes(sortPriority[i])) {
      sort = {
        field: `metrics.${sortPriority[i]}`,
        direction: 'desc',
      }
      break
    }
  }

  return (
    <div class='evaluations-table-metrics' style={{ height: '390px', overflow: 'auto' }}>
      <EuiInMemoryTable
        columns={columns}
        itemId='strategy_id'
        items={items}
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