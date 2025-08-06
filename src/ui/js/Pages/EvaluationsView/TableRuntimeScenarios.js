/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useState } from 'react'
import {
  EuiBadge,
  EuiButtonIcon,
  EuiCode,
  EuiCodeBlock,
  EuiIcon,
  EuiInMemoryTable,
  EuiPanel,
  EuiScreenReaderOnly,
  EuiToolTip,
} from '@elastic/eui'
import utils from '../../utils'

const TableRuntimeScenarios = ({ items }) => {

  ////  State  /////////////////////////////////////////////////////////////////

  const [itemsToExpandedRows, setItemIdToExpandedRowMap] = useState({})

  const toggleDetails = (item) => {
    setItemIdToExpandedRowMap(prev => {
      const next = { ...prev }
      next[item._id] ? delete next[item._id] : (next[item._id] = renderDetails(item))
      return next
    })
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderDetails = (item) => {
    return (
      <EuiPanel color='transparent' paddingSize='none'>
        <EuiCodeBlock
          isCopyable
          language='json'
          paddingSize='m'
          overflowHeight={300}
          style={{ width: '100%' }}
        >
          {utils.jsonStringifySortedKeys(item, null, 2)}
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
              _itemsToExpandedRows[item._id] ? 'Collapse' : 'Expand'
            }
            iconType={
              _itemsToExpandedRows[item._id] ? 'arrowDown' : 'arrowRight'
            }
          />
        )
      },
    },
    {
      field: 'name',
      name: 'Scenario',
      sortable: true,
      truncateText: true,
      width: '100px',
      render: (name, item) => item.name
    },
    {
      field: 'values',
      name: 'Values',
      render: (name, item) => {
        return (
          <div style={{ width: '100%' }}>
            <EuiCodeBlock
              language='json'
              paddingSize='xs'
              style={{ fontSize: '11px' }}
              transparentBackground
            >
              {JSON.stringify(item.values)}
            </EuiCodeBlock>
          </div>
        )
      },
    },
    {
      field: 'tags',
      name: 'Tags',
      width: '100px',
      render: (name, item) => {
        const tags = (item.tags ?? []).map(tag => (
          <EuiBadge color='hollow' key={tag}>
            {tag}
          </EuiBadge>
        ))
        return tags
      },
    },
    {
      field: '_fingerprint',
      style: { width: '275px' },
      name: <>
        <EuiToolTip content='A hash of the scenario values. If this fingerprint changes between evaluations, it can affect relevance metrics in subsequent evaluations.'>
          <span>
            Fingerprint <EuiIcon type='question' />
          </span>
        </EuiToolTip>
      </>,
      render: (name, item) => (
        <EuiCode transparentBackground style={{ color: 'inherit', fontSize: '12px', fontWeight: 'normal', padding: 0 }}>
          {item._fingerprint}
        </EuiCode>
      )
    }
  ]

  return (
    <EuiInMemoryTable
      allowNeutralSort={false}
      columns={columns}
      itemId='_id'
      itemIdToExpandedRowMap={itemsToExpandedRows}
      items={items}
      pagination={true}
      responsiveBreakpoint={false}
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
            options: Array.from(new Set(items.flatMap(({ tags }) => tags ?? []))).map(tag => ({
              value: tag
            })),
            type: 'field_value_selection',
          },
        ]
      }}
      sorting={{
        sort: {
          field: 'name',
          direction: 'asc',
        }
      }}
      tableLayout='auto'
    />
  )
}

export default TableRuntimeScenarios