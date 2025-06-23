import React, { useState } from 'react'
import {
  EuiButtonIcon,
  EuiCodeBlock,
  EuiIcon,
  EuiInMemoryTable,
  EuiPanel,
  EuiScreenReaderOnly,
  EuiToolTip,
} from '@elastic/eui'

const TableRuntimeIndices = ({ items }) => {

  const [itemsToExpandedRows, setItemIdToExpandedRowMap] = useState({})

  const toggleDetails = (item) => {
    setItemIdToExpandedRowMap(prev => {
      const next = { ...prev }
      next[item._id] ? delete next[item._id] : (next[item._id] = renderDetails(item))
      return next
    })
  }

  const renderDetails = (item) => {
    const _item = { ...item }
    delete _item._id
    return (
      <EuiPanel color='transparent' paddingSize='none'>
        <EuiCodeBlock
          isCopyable
          language='json'
          paddingSize='m'
          overflowHeight={300}
          style={{ width: '100%' }}
        >
          {JSON.stringify(_item, null, 2)}
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
      field: 'index',
      name: 'Index',
      sortable: true,
      truncateText: true,
      render: (name, item) => item.index
    },
    {
      field: 'uuid',
      name: 'UUID',
      render: (name, item) => item.uuid
    },
    {
      field: 'fingerprint',
      name: <>
        <EuiToolTip content='A hash of the index UUID and the max_seq_no of its shards. If this fingerprint changes between evaluations, it means the index executed write operations, which can affect relevance metrics in subsequent evaluations.'>
          <span>
            Fingerprint <EuiIcon type='question' />
          </span>
        </EuiToolTip>
      </>,
      render: (name, item) => item.fingerprint
    }
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
        }
      }}
      sorting={{
        sort: {
          field: 'index',
          direction: 'asc',
        }
      }}
      tableLayout='auto'
    />
  )
}

export default TableRuntimeIndices