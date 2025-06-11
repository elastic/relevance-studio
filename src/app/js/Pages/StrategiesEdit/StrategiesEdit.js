import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import {
  EuiButton,
  EuiFlexGroup,
  EuiFlexItem,
  EuiForm,
  EuiFormRow,
  EuiPanel,
  EuiSkeletonText,
  EuiSkeletonTitle,
  EuiSpacer,
} from '@elastic/eui'
import api from '../../api'
import utils from '../../utils'
import { Page } from '../../Layout'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'
import FlyoutHelp from './FlyoutHelp'

const StrategiesEdit = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, darkMode } = useAppContext()
  const { project } = useProjectContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [loadingStrategy, setLoadingStrategy] = useState(true)
  const [params, setParams] = useState([])
  const [showHelp, setShowHelp] = useState(false)
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
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to get strategy' }))
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
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to update display' }))
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
          fontSize: 12,
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

  const buttonHelp = (
    <EuiButton
      color='text'
      iconType='help'
      onClick={() => setShowHelp(!showHelp)}>
      Help
    </EuiButton>
  )

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
    } buttons={[buttonHelp]}>
      {showHelp && <FlyoutHelp onClose={() => setShowHelp(false)} />}
      <EuiFlexGroup alignItems='flexStart' style={{ height: 'calc(100vh - 135px)' }}>

        {/* Editor */}
        <EuiFlexItem grow={5}>

          {/* Editor controls */}
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
                    <div style={{ height: 'calc(100vh - 200px)' }}>
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

            </EuiForm>
          </EuiPanel>
        </EuiFlexItem>

      </EuiFlexGroup>
    </Page >
  </>)
}

export default StrategiesEdit