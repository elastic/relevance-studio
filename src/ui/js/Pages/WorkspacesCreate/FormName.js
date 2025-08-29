/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  EuiFieldText,
  EuiFormRow,
} from '@elastic/eui'

const FormName = ({ onChange, value }) => {
  return (
    <EuiFormRow style={{ width: '500px' }}>
      <EuiFieldText
        aria-label='Name'
        autocomplete='off'
        autoFocus
        onChange={onChange}
        style={{
          fontSize: '18px',
          fontWeight: 600,
          padding: '24px',
          textAlign: 'center'
        }}
        value={value}
      />
    </EuiFormRow>
  )
}

export default FormName