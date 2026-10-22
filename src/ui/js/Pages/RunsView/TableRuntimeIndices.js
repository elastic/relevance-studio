/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useState } from 'react'
import {
  EuiBasicTable,
  EuiButtonIcon,
  EuiCode,
  EuiCodeBlock,
  EuiIcon,
  EuiPanel,
  EuiScreenReaderOnly,
  EuiToolTip,
} from '@elastic/eui'
import utils from '../../utils'

// Items are a single server-fetched page (see FlyoutRuntime). Sorting here is
// therefore local to that page, not the full collection.
const TableRuntimeIndices = ({ items }) => {

  ////  State  /////////////////////////////////////////////////////////////////

  const [itemsToExpandedRows, setItemIdToExpandedRowMap] = useState({})
  const [sort, setSort] = useState({ field: '_index', direction: 'asc' })

  const toggleDetails = (item) => {
    setItemIdToExpandedRowMap(prev => {
      const next = { ...prev }
      next[item._id] ? delete next[item._id] : (next[item._id] = renderDetails(item))
      return next
    })
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderDetails = (item) => {
    const _item = { ...item }
    delete _item._id
    return (
      <EuiPanel color='transparent' paddingSize='none'>
        <EuiCodeBlock
          isCopyable
          language='json'
          paddingSize='m'
          overflowHeight={400}
          style={{ width: '100%' }}
        >
          {utils.jsonStringifySortedKeys(_item, null, 2)}
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
      field: '_index',
      name: 'Index',
      sortable: true,
      truncateText: true,
      render: (name, item) => item._index
    },
    {
      field: 'settings.index.creation_date',
      name: 'Created',
      render: (name, item) => item.settings?.index?.creation_date ? new Date(Number(item.settings?.index?.creation_date)).toISOString() : ''
    },
    {
      field: 'settings.index.uuid',
      name: 'UUID',
      style: { width: '200px' },
      render: (name, item) => (
        <EuiCode transparentBackground style={{ color: 'inherit', fontSize: '12px', fontWeight: 'normal', padding: 0 }}>
          {item.settings?.index?.uuid}
        </EuiCode>
      )
    },
    {
      field: '_fingerprint',
      style: { width: '275px' },
      name: <>
        <EuiToolTip content='A hash of the index UUID and the max_seq_no of its shards. If this fingerprint changes between runs, it means the index executed write operations, which can affect relevance metrics in subsequent runs.'>
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

  const sortedItems = utils.sortDocs(items, sort.field, sort.direction)

  return (
    <EuiBasicTable
      columns={columns}
      itemId='_id'
      itemIdToExpandedRowMap={itemsToExpandedRows}
      items={sortedItems}
      onChange={({ sort: newSort }) => {
        if (newSort) setSort(newSort)
      }}
      responsiveBreakpoint={false}
      sorting={{
        sort,
      }}
      tableLayout='auto'
    />
  )
}

export default TableRuntimeIndices