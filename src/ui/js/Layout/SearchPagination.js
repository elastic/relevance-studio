/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { EuiTablePagination } from '@elastic/eui'

const SearchPagination = ({ onChangePage, onChangeSize, page, size, total }) => {
  return (
    <EuiTablePagination
      activePage={page - 1}
      itemsPerPage={size}
      itemsPerPageOptions={[10, 50, 100]}
      pageCount={Math.ceil(total / size)}
      onChangePage={(i) => onChangePage(i + 1)}
      onChangeItemsPerPage={(size) => {
        onChangeSize(size)
        onChangePage(1) // reset to first page
      }}
    />
  )
}

export default SearchPagination