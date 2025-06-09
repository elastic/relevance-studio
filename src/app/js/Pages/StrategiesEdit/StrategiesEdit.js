import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiCode,
  EuiFlexGroup,
  EuiFlexItem,
  EuiForm,
  EuiFormRow,
  EuiLink,
  EuiPanel,
  EuiSkeletonText,
  EuiSkeletonTitle,
  EuiSpacer,
  EuiText
} from '@elastic/eui'
import api from '../../api'
import utils from '../../utils'
import { Page } from '../../Layout'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'

const StrategiesEdit = () => {
  
  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, darkMode } = useAppContext()
  const { project } = useProjectContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [loadingStrategy, setLoadingStrategy] = useState(true)
  const [params, setParams] = useState([])
  const [showHelp, setShowHelp] = useState(true)
  const [strategy, setStrategy] = useState({})
  const [strategyDraft, setStrategyDraft] = useState('')
  const [strategyId, setStrategyId] = useState(null)

  /**
   * Parse strategyId from URL path
   */
  const { strategy_id } = useParams()
  useEffect(() => setStrategyId(strategy_id), [strategy_id])

  /**
   * Get strategy on load
   */
  useEffect(() => {
    if (!project?._id || strategyId == null)
      return
    (async () => {
    
      // Submit API request
      let response
      try {
        setLoadingStrategy(true)
        response = await api.get_strategy(project._id, strategyId)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to get strategy'
        }))
      } finally {
        setLoadingStrategy(false)
      }

      // Handle API response
      setStrategy(response.data._source)
    })()
  }, [project, strategyId])

  /**
   * Get strategy draft from strategy document
   */
  useEffect(() => {
    if (!strategy.template)
      return
    setStrategyDraft(JSON.stringify(strategy.template.source, null, 2))
  }, [strategy.template])

  /**
   * Extract params (formatted as Mustache variables) from a JSON string.
   */
  const RE_PARAMS = /{{\s*([\w.]+)\s*}}/g
  const extractParams = (jsonString) => {
    const matches = new Set()
    let match
    while ((match = RE_PARAMS.exec(jsonString)) !== null)
      matches.add(match[1])
    setParams(matches)
  }

  /**
   * Extract params from the strategy draft when the draft changes.
   */
  useEffect(() => {
    extractParams(strategyDraft)
  }, [strategyDraft])

  const onSaveStrategy = (e) => {
    e.preventDefault();
    (async () => {
        
      // Submit API request
      const doc = {
        name: strategy.name,
        tags: strategy.tags,
        template: {
          source: JSON.parse(strategyDraft)
        },
      }
      let response
      try {
        setLoadingStrategy(true)
        response = await api.update_strategy(project._id, strategyId, doc)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to update display'
        }))
      } finally {
        setLoadingStrategy(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Saved strategy',
        color: 'success',
        iconType: 'check'
      })
      setStrategy(doc)
    })()
  }

  /**
   * Check if the strategy draft differs from the saved strategy.
   */
  const doesDraftDiffer = () => {
    try {
      return JSON.stringify(strategy.template?.source || '{}') == JSON.stringify(JSON.parse(strategyDraft || '{}'))
    } catch (e) {
      return undefined
    }
  }


  ////  Render  ////////////////////////////////////////////////////////////////

  const renderEditor = () => {
    return (
      <Editor
        defaultLanguage='json'
        height='100%'
        onChange={(value, event) => setStrategyDraft(value)}
        options={{
          fontSize: 10,
          insertSpaces: true,
          lineNumbers: 'on',
          minimap: {
            enabled: false
          },
          renderLineHighlight: false,
          renderOverviewRuler: false,
          scrollBeyondLastLine: false,
          stickyScroll: {
            enabled: false,
          },
          tabSize: 2
        }}
        theme={darkMode ? 'vs-dark' : 'light'}
        value={strategyDraft}
      />
    )
  }

  const renderCalloutStrategy = () => {
    return (
      <EuiCallOut iconType='help' onDismiss={()=>setShowHelp(false)} title='How to use this editor'>
        <EuiSpacer size='s' />
        <EuiText size='xs'>
          <h4>
            What is a strategy?
          </h4>
          <p>
            A strategy is a retriever or query that you want to test in your search relevance evaluations. It becomes the contents of the <EuiCode>"source"</EuiCode> field of a <EuiLink href='https://www.elastic.co/docs/solutions/search/search-templates' target='_blank'>search template</EuiLink> in the <EuiLink href='https://www.elastic.co/guide/en/elasticsearch/reference/8.18/search-rank-eval.html' target='_blank'>Ranking Evaluation API</EuiLink>.
          </p>
          <h4>
            How do I pass inputs to the strategy?
          </h4>
          <p>
            Use <EuiLink href='https://www.elastic.co/docs/solutions/search/search-templates#create-search-template' target='_blank'>double curly braces</EuiLink> to define params, which indicate where your strategy will accept inputs. If the input will be a string, be sure to surround the variable with double quotes. Example: <EuiCode>{'"{{ text }}"'}</EuiCode>
          </p>
        </EuiText>
      </EuiCallOut>
    )
  }

  const renderCalloutParams = () => {
    const _params = []
    params.forEach((param, i) => _params.push(
      <EuiBadge color='hollow' key={i}>
        <EuiCode transparentBackground>{param}</EuiCode>
      </EuiBadge>
    ))

    return (
      <EuiPanel paddingSize='none' hasBorder={!!params.size} hasShadow={false}>
        <EuiCallOut
          color={!params.size ? 'warning' : 'text'}
          iconType={!params.size ? 'warning' : null}
          title={!params.size ? 'Your strategy has no params' : 'Your strategy has these params:'}
        >
          <EuiSpacer size='s' />
          <EuiText size='xs'>
          {!params.size &&
            <EuiText size='xs'>
              <p>
                Your strategy won't use inputs until you give it variables.
              </p>
              <p>
                Example: <EuiCode>{'"{{ text }}"'}</EuiCode>
              </p>
            </EuiText>
          }
            {_params}
          </EuiText>
        </EuiCallOut>
      </EuiPanel>
    )
  }

  return (<>
    <Page title={
      <EuiSkeletonTitle isLoading={loadingStrategy} size='l'>
        {!strategy.name &&
          <>Not found</>
        }
        {!!strategy.name &&
          <>{strategy.name}</>
        }
      </EuiSkeletonTitle>
    }>
      <EuiFlexGroup style={{ height: 'calc(100vh - 135px)' }}>
        <EuiFlexItem grow={5}>
          <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none'>
            <EuiForm>

              {/* Buttons */}
              <EuiFlexGroup gutterSize='s'>
                <EuiFlexItem grow={false}>
                  <EuiButton
                    color='primary'
                    disabled={loadingStrategy || doesDraftDiffer()}
                    fill
                    onClick={onSaveStrategy}
                    type='submit'
                  >
                    Save
                  </EuiButton>
                </EuiFlexItem>
                <EuiFlexItem grow={false}>
                  <EuiButton
                    color='text'
                    disabled={loadingStrategy || doesDraftDiffer()}
                    onClick={() => { setStrategyDraft(JSON.stringify(strategy.template.source, null, 2)) }}
                  >
                    Reset
                  </EuiButton>
                </EuiFlexItem>
              </EuiFlexGroup>
              <EuiSpacer size='m' />

              {/* Editor */}
              <EuiFormRow fullWidth label='Query DSL editor'>
                <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none'>
                  <EuiSkeletonText lines={21} isLoading={loadingStrategy}>
                    <div style={{ height: 'calc(100vh - 300px)' }}>
                      <EuiPanel
                        hasBorder
                        paddingSize='none'
                        style={{
                          position: 'absolute',
                          top: '0',
                          bottom: '14px',
                          left: '0',
                          right: '0'
                        }}
                      >
                        {renderEditor()}
                      </EuiPanel>
                    </div>
                  </EuiSkeletonText>
                </EuiPanel>
              </EuiFormRow>
              <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0 }}>
                { strategyDraft && renderCalloutParams() }
              </div>

            </EuiForm>
          </EuiPanel>
        </EuiFlexItem>

        {/* Details */}
        <EuiFlexItem grow={5}>
          <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none'>

            {/* Help: Strategies */}
            { showHelp && renderCalloutStrategy() }
            { showHelp && <EuiSpacer size='m' /> }
            
          </EuiPanel>
        </EuiFlexItem>
      </EuiFlexGroup>
    </Page>
  </>)
}

export default StrategiesEdit