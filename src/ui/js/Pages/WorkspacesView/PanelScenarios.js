/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiInMemoryTable,
  EuiProgress,
  EuiText,
} from '@elastic/eui'
import utils from '../../utils'

const PanelScenarios = ({ evaluation, rowOnHover }) => {

  ////  State  /////////////////////////////////////////////////////////////////

  const [items, setItems] = useState([])


  ////  Render  ////////////////////////////////////////////////////////////////

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

  return (
    <div className='evaluations-table-metrics' style={{ height: '390px', overflow: 'auto' }}>
      <EuiInMemoryTable
        columns={columns}
        itemId='strategy_id'
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

export default PanelScenarios