/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useRef } from 'react'
import {
  EuiFormRow,
  EuiMarkdownEditor,
} from '@elastic/eui'

const FormDescription = ({ onChange, value }) => {

  /**
   * Auto-focus on the editor
   */
  const editorRef = useRef(null)
  useEffect(() => editorRef.current?.textarea?.focus(), [])

  return (
    <EuiFormRow>
      <EuiMarkdownEditor
        aria-label='Description'
        class='editor'
        height={150}
        onChange={onChange}
        ref={editorRef}
        style={{ width: '600px' }}
        value={value}
        uiPlugins={[]}
      />
    </EuiFormRow>
  )
}

export default FormDescription