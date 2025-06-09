import React from 'react'
import {
  EuiFlexGroup,
  EuiFlexItem,
  EuiHorizontalRule,
  EuiMarkdownFormat,
  EuiPanel,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'

const DocCard = (props) => {

  ////  Props  /////////////////////////////////////////////////////////////////

  const doc = props.doc
  const template = props.template

  /**
   * Replace mustache variables in the markdown template with values from the doc.
   */
  const RE_MUSTACHE_VARIABLES = /{{\s*([\w.]+)\s*}}/g
  const replaceMustacheVariables = (_template, doc) => {
    const values = { _id: doc._id, _index: doc._index, ...doc._source }
    const content = _template.replace(RE_MUSTACHE_VARIABLES, (_, path) => {
      const keys = path.split('.')
      let value = values
      for (const key of keys) {
        if (value == null || !(key in value)) return `{{ ${path} }}`
        value = value[key]
      }
      return value;
    })
    return content
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const panelProps = {
    hasBorder: true,
    hasShadow: false,
    paddingSize: 'none',
    ...props.panelProps
  }

  const description = <>
    <EuiPanel
      hasBorder={false}
      hasShadow={false}
      paddingSize='m'
      style={{
        height: '200px',
        overflow: 'scroll',
        maskImage: 'linear-gradient(to bottom, black calc(100% - 40px), transparent 100%)'
      }}
    >
      <EuiMarkdownFormat textSize='xs'>
        {replaceMustacheVariables(template, doc)}
      </EuiMarkdownFormat>
    </EuiPanel>
    <EuiSpacer size='xs' />
    <EuiHorizontalRule margin='none' />
    <EuiPanel hasBorder={false} hasShadow={false} paddingSize='s'>
      <EuiFlexGroup alignItems='center' gutterSize='none'>
        <EuiFlexItem grow>
          <EuiText color='subdued' size='xs' style={{ paddingLeft: '8px' }}>
            <small>{doc._index}:{doc._id}</small>
          </EuiText>
        </EuiFlexItem>
      </EuiFlexGroup>
    </EuiPanel>
  </>

  return (
    <EuiPanel className='doc-card' { ...panelProps }>
      {description}
    </EuiPanel>
  )
}

export default DocCard