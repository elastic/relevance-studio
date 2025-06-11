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

const DocCard = ({ body, doc, imagePosition, imageUrl, ...props }) => {

  /**
   * Replace mustache variables in the markdown template with values from the doc.
   */
  const RE_MUSTACHE_VARIABLES = /{{\s*([\w.]+)\s*}}/g
  const replaceMustacheVariables = (template, doc) => {
    const values = { _id: doc._id, _index: doc._index, ...doc._source }
    const rendered = template.replace(RE_MUSTACHE_VARIABLES, (_, path) => {
      const keys = path.split('.')
      let value = values
      for (const key of keys) {
        if (value == null || !(key in value)) return `{{ ${path} }}`
        value = value[key]
      }
      return value
    })
    return rendered
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const panelProps = {
    hasBorder: true,
    hasShadow: false,
    paddingSize: 'none',
    ...props.panelProps
  }

  const renderImage = () => {
    const style = {
      background: `url('${replaceMustacheVariables(imageUrl, doc)}')`,
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat',
      backgroundSize: 'contain',
      width: '100%'
    }
    switch (imagePosition) {
      case 'left':
        style.height = '100%'
        break
      case 'top-left':
        style.height = '120px'
        break
      case 'top-right':
        style.height = '120px'
        break
      case 'right':
        style.height = '100%'
        break
      default:
        break
    }
    return (
      <EuiPanel
        hasBorder={false}
        hasShadow={false}
        paddingSize='none'
        style={style}
      >
      </EuiPanel>
    )
  }

  const renderBody = () => {
    return (
      <EuiMarkdownFormat style={{ display: 'inline' }} textSize='xs'>
        {replaceMustacheVariables(body, doc)}
      </EuiMarkdownFormat>
    )
  }

  const renderContent = () => {
    if (!imageUrl || !imagePosition)
      return renderBody()
    if (imagePosition == 'top-left') {
      return (<>
        <div style={{
          display: 'inline',
          float: 'left',
          margin: '0 12px 12px 0',
          width: '33%'
        }}>
          {renderImage()}
        </div>
        <div style={{ display: 'inline' }}>
          {renderBody()}
        </div>
      </>)
    } else if (imagePosition == 'top-right') {
      return (<>
        <div style={{
          display: 'inline',
          float: 'right',
          margin: '0 0 12px 12px',
          width: '33%'
        }}>
          {renderImage()}
        </div>
        <div style={{ display: 'inline' }}>
          {renderBody()}
        </div>
      </>)
    }
  }

  return (
    <EuiPanel className='doc-card' {...panelProps}>
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
        {renderContent()}
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
    </EuiPanel>
  )
}

export default DocCard