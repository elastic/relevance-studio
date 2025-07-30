/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License;
 * you may not use this file except in compliance with the Elastic License.
 */

import { EuiText } from '@elastic/eui'

const SearchCount = ({ showing, total }) => {
  return (
    <EuiText color='subdued' size='xs'>
      Showing {showing.toLocaleString()} of {total.toLocaleString()}{total >= 10000 ? '+' : ''} result{total != 1 ? 's' : ''}
    </EuiText>
  )
}

export default SearchCount