/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License;
 * you may not use this file except in compliance with the Elastic License.
 */

import {
  EuiBasicTable,
  EuiButton,
  EuiFlexGroup,
  EuiFlexItem,
  EuiForm,
  EuiPanel,
  EuiSearchBar,
  EuiSpacer,
  EuiSwitch,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../Contexts/AppContext'
import {
  SearchCount,
  SearchPagination,
} from '.'

const SearchTable = ({
  docs,
  total,
  page,
  size,
  sortField,
  sortOrder,
  isLoading,
  columns,
  text,
  onChangeText,
  onChangePage,
  onChangeSize,
  onChangeSort,
  onSubmit,
  showAutoRefresh = false,
}) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { autoRefresh, setAutoRefresh } = useAppContext()

  return (
    <EuiForm component='form' onSubmit={onSubmit}>

      {/* Search bar */}
      <EuiFlexGroup gutterSize='s'>
        <EuiFlexItem grow>
          <EuiSearchBar
            box={{ incremental: true, schema: true }}
            defaultQuery={text}
            onChange={(q) => onChangeText(q.query?.text || '')}
          />
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiButton isLoading={isLoading} iconType='search' type='submit'>
            Search
          </EuiButton>
        </EuiFlexItem>
      </EuiFlexGroup>
      <EuiSpacer size='xs' />

      {/* Search results count and auto-refresh */}
      <EuiPanel color='transparent' paddingSize='s'>
        <EuiFlexGroup>

          {/* Search results count */}
          <EuiFlexItem>
            {total !== null &&
              <SearchCount showing={docs.length} total={total} />
            }
          </EuiFlexItem>

          {/* Auto-refresh */}
          {showAutoRefresh &&
            <EuiFlexItem grow={false}>
              <EuiSwitch
                checked={autoRefresh}
                compressed
                label={
                  <EuiText color={autoRefresh ? 'text' : 'subdued'} size='xs'>
                    Auto-refresh
                  </EuiText>
                }
                onChange={() => setAutoRefresh(!autoRefresh)}
                style={{ align: 'right' }}
              />
            </EuiFlexItem>
          }
        </EuiFlexGroup>
      </EuiPanel>
      <EuiSpacer size='s' />

      {/* Search results table */}
      <EuiBasicTable
        columns={columns}
        items={docs}
        loading={isLoading}
        onChange={({ sort }) => {
          if (sort)
            onChangeSort(sort.field, sort.direction)
        }}
        sorting={{
          sort: {
            field: sortField,
            direction: sortOrder
          }
        }}
        tableLayout='auto'
      />
      <EuiSpacer size='m' />

      {/* Pagination */}
      {total !== null &&
        <SearchPagination
          page={page}
          size={size}
          total={total}
          onChangePage={onChangePage}
          onChangeSize={onChangeSize}
        />
      }
    </EuiForm>
  )
}

export default SearchTable