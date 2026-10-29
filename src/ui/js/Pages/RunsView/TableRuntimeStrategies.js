/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useState } from 'react'
import {
  EuiBadge,
  EuiBasicTable,
  EuiButtonIcon,
  EuiCode,
  EuiCodeBlock,
  EuiIcon,
  EuiInMemoryTable,
  EuiPanel,
  EuiScreenReaderOnly,
  EuiSpacer,
  EuiText,
  EuiToolTip,
} from '@elastic/eui'
import hp from '../../hyperparameters'
import utils from '../../utils'

const TableRuntimeStrategies = ({ items }) => {

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
    const space = item._resolved_hyperparameters || []
    return (
      <EuiPanel color='transparent' paddingSize='none'>
        {space.length > 0 &&
          <>
            <EuiText size='xs'>
              <b>Hyperparameters</b>{' '}
              <EuiBadge color='hollow'>{item._algorithm || 'grid'} search</EuiBadge>
              <EuiBadge color='hollow'>{item._variant_count || 1} variants</EuiBadge>
            </EuiText>
            <EuiSpacer size='xs' />
            <EuiBasicTable
              columns={[
                { field: 'name', name: 'Name', render: (n) => <EuiText size='xs'><b>{n}</b></EuiText> },
                { field: 'type', name: 'Type' },
                { field: 'promoted_value', name: 'Promoted value', render: (v) => hp.formatValue(v) },
                {
                  field: 'testable_values',
                  name: 'Valid testable values',
                  render: (testable) => hp.describeTestableValues(testable),
                },
                {
                  field: 'values_to_test',
                  name: 'Values tested in this run',
                  render: (values) => hp.describeValuesToTest(values),
                },
              ]}
              itemId='name'
              items={space}
              responsiveBreakpoint={false}
            />
            <EuiSpacer size='s' />
          </>
        }
        <EuiCodeBlock
          isCopyable
          language='json'
          paddingSize='m'
          overflowHeight={400}
          style={{ width: '100%' }}
        >
          {utils.jsonStringifySortedKeysWithTripleQuotes(item)}
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
      name: 'Strategy',
      sortable: true,
      truncateText: true,
      render: (name, item) => item.name
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
      field: '_variant_count',
      name: 'Variants',
      width: '80px',
      render: (count) => count || 1,
    },
    {
      field: '_fingerprint',
      style: { width: '275px' },
      name: <>
        <EuiToolTip content='A hash of the strategy template. If this fingerprint changes between runs, it can affect relevance metrics in subsequent runs.'>
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

export default TableRuntimeStrategies