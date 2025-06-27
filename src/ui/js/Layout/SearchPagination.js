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