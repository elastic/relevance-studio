/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  EuiIcon,
  EuiPanel,
  EuiSpacer,
  EuiText,
  EuiTitle,
} from '@elastic/eui'
import { Page } from '../../Layout'

const NotFound = () => {

  ////  Render  ////////////////////////////////////////////////////////////////

  return (
    <Page panelled>
      <EuiPanel color='transparent'>
        <div style={{ textAlign: 'center' }}>
          <EuiSpacer />
          <EuiIcon color='primary' size='xxl' type='cloudDrizzle' />
          <EuiSpacer size='xxl' />
          <EuiTitle size='l'>
            <h1><big>Hmm...</big></h1>
          </EuiTitle>
          <EuiSpacer />
          <EuiText>
            <p>
              That page doesn't seem to exist.
            </p>
          </EuiText>
        </div>
      </EuiPanel>
    </Page>
  )
}

export default NotFound