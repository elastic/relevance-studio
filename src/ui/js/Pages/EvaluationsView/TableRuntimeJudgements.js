import React, { useState } from 'react'
import {
  EuiButtonIcon,
  EuiCodeBlock,
  EuiInMemoryTable,
  EuiPanel,
  EuiScreenReaderOnly,
} from '@elastic/eui'

const TableRuntimeJudgements = ({ items }) => {

  const [itemsToExpandedRows, setItemIdToExpandedRowMap] = useState({})

  const toggleDetails = (item) => {
    setItemIdToExpandedRowMap(prev => {
      const next = { ...prev }
      next[item._id] ? delete next[item._id] : (next[item._id] = renderDetails(item))
      return next
    })
  }

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
          {JSON.stringify(item, null, 2)}
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
      field: 'scenario_id',
      name: 'Scenario',
      sortable: true,
      truncateText: true,
      render: (name, item) => item.scenario_id
    },
    {
      field: 'index',
      name: 'Index',
      sortable: true,
      truncateText: true,
      render: (name, item) => item.index
    },
    {
      field: 'doc_id',
      name: 'Doc _id',
      sortable: true,
      truncateText: true,
      render: (name, item) => item.doc_id
    },
    {
      field: 'rating',
      name: 'Rating',
      sortable: true,
      width: '100px',
      render: (name, item) => item.rating
    },
  ]

  return (
    <EuiInMemoryTable
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
            field: 'index',
            multiSelect: 'or',
            name: 'Index',
            options: Array.from(new Set(items.map(({ index }) => index))).map(index => ({
              value: index
            })),
            type: 'field_value_selection',
          },
          {
            autoSortOptions: false,
            field: 'doc_id',
            multiSelect: 'or',
            name: 'Doc _id',
            options: Array.from(new Set(items.map(({ doc_id }) => doc_id))).map(doc_id => ({
              value: doc_id
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

export default TableRuntimeJudgements