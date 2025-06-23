import React, { useState } from 'react'
import {
  EuiBadge,
  EuiButtonIcon,
  EuiCodeBlock,
  EuiInMemoryTable,
  EuiPanel,
  EuiScreenReaderOnly,
} from '@elastic/eui'

const TableRuntimeScenarios = ({ items }) => {

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
        const tags = []
        for (var i in item.tags)
          tags.push(
            <EuiBadge color='hollow' key={item.tags[i]}>
              {item.tags[i]}
            </EuiBadge>
          )
        return tags
      },
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