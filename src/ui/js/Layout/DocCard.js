/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  EuiCodeBlock,
  EuiFlexGroup,
  EuiFlexItem,
  EuiHorizontalRule,
  EuiMarkdownFormat,
  EuiPanel,
  EuiSpacer,
  EuiText,
  EuiToolTip,
} from '@elastic/eui'

const DocCard = ({ body, doc, imagePosition, imageUrl, showScore = false, ...props }) => {

  /**
   * Replace mustache variables in the markdown template with values from the doc.
   */
  const RE_MUSTACHE_VARIABLES = /{{\s*([\w.-]+)\s*}}/g
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
    paddingSize: 'none',
    ...props.panelProps
  }

  const renderImage = () => {
    const style = {
      backgroundImage: `url('${replaceMustacheVariables(imageUrl, doc)}')`,
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

  const renderContentRich = () => {
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

  /**
   * Indent JSON, but don't indent arrays that contain non-object values.
   * This will prevent dense vectors from dominating the display.
   */
  const customStringify = (obj, indent = 2, level = 0) => {
    const spacing = ' '.repeat(indent * level);
    if (Array.isArray(obj)) {
      const isAllPrimitives = obj.every(
        item => item === null || ['string', 'number', 'boolean'].includes(typeof item)
      );
      if (isAllPrimitives) {
        return `[ ${obj.map(item => JSON.stringify(item)).join(', ')} ]`;
      } else {
        return '[ \n' + obj.map(item =>
          spacing + ' '.repeat(indent) + customStringify(item, indent, level + 1)
        ).join(',\n') + '\n' + spacing + ' ]';
      }
    }
    if (obj && typeof obj === 'object') {
      const entries = Object.entries(obj).map(([key, value]) => {
        const keyStr = JSON.stringify(key);
        const valStr = customStringify(value, indent, level + 1);
        return spacing + ' '.repeat(indent) + `${keyStr}: ${valStr}`;
      });
      return `{\n${entries.join(',\n')}\n${spacing}}`;
    }
    return JSON.stringify(obj);
  }


  const renderContentJson = () => (
    <EuiCodeBlock
      isCopyable
      isVirtualized
      language='json'
      overflowHeight={'100%'}
      paddingSize='s'
    >
      {customStringify(doc?._source, 2)}
    </EuiCodeBlock>
  )

  return (
    <EuiPanel className='doc-card' {...panelProps}>
      <EuiPanel
        hasBorder={false}
        hasShadow={false}
        paddingSize={!body ? 'xs' : 'm'}
        style={{
          height: '200px',
          overflow: 'scroll',
          maskImage: 'linear-gradient(to bottom, black calc(100% - 40px), transparent 100%)'
        }}
      >
        {!body ? renderContentJson() : renderContentRich()}
      </EuiPanel>
      <EuiSpacer size='xs' />
      <EuiHorizontalRule margin='none' />
      <EuiPanel hasBorder={false} hasShadow={false} paddingSize='s'>
        <EuiFlexGroup alignItems='center' gutterSize='s'>
          <EuiFlexItem grow={false}>
            <EuiText color='subdued' size='xs' style={{ paddingLeft: '8px' }}>
              <EuiToolTip content='Index'>
                <small>{doc._index}</small>
              </EuiToolTip>
            </EuiText>
          </EuiFlexItem>
          <EuiFlexItem grow={false}>
            <EuiText color='subdued' size='xs' style={{ paddingRight: '8px', textAlign: 'right' }}>
              <EuiToolTip content='_id'>
                <small>{doc._id}</small>
              </EuiToolTip>
            </EuiText>
          </EuiFlexItem>
          {showScore &&
            <EuiFlexItem grow={5}>
              <EuiText color='subdued' size='xs' style={{ paddingRight: '8px', textAlign: 'right' }}>
                <EuiToolTip content='Score'>
                  <small>{doc._score}</small>
                </EuiToolTip>
              </EuiText>
            </EuiFlexItem>
          }
        </EuiFlexGroup>
      </EuiPanel>
    </EuiPanel>
  )
}

export default DocCard