import { EuiText } from '@elastic/eui'

const SearchCount = ({ showing, total }) => {
  return (
    <EuiText color='subdued' size='xs'>
      Showing {showing.toLocaleString()} of {total.toLocaleString()}{total >= 10000 ? '+' : ''} result{total != 1 ? 's' : ''}
    </EuiText>
  )
}

export default SearchCount