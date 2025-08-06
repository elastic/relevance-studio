/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import {
  EuiBadge,
  EuiButton,
  EuiCode,
  EuiCodeBlock,
  EuiFlexGroup,
  EuiFlexItem,
  EuiIcon,
  EuiPanel,
  EuiProgress,
  EuiResizableContainer,
  EuiSkeletonTitle,
  EuiSpacer,
  EuiSwitch,
  EuiText,
} from '@elastic/eui'
import { debounce } from 'lodash'
import { useAppContext } from '../../Contexts/AppContext'
import { usePageResources, useResources, useAdditionalResources } from '../../Contexts/ResourceContext'
import {
  Page,
  SelectScenario,
  SearchResultsJudgements
} from '../../Layout'
import FlyoutHelp from './FlyoutHelp'
import api from '../../api'
import utils from '../../utils'

const StrategiesEdit = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, darkMode } = useAppContext()
  const { workspace, strategy, displays } = usePageResources()
  useAdditionalResources(['displays'])
  const isReady = useResources().hasResources(['workspace', 'strategy', 'displays'])

  ////  State  /////////////////////////////////////////////////////////////////

  // Strategy editing
  const [isProcessing, setIsProcessing] = useState(false)
  const [params, setParams] = useState([])
  const [showHelp, setShowHelp] = useState(false)
  const [strategyDraft, setStrategyDraft] = useState('')

  // Strategy testing
  const [errorContent, setErrorContent] = useState(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [indexPatternMap, setIndexPatternMap] = useState({})
  const [isLoadingScenarios, setIsLoadingScenarios] = useState(false)
  const [isLoadingResults, setIsLoadingResults] = useState(false)
  const [isRankEvalEnabled, setIsRankEvalEnabled] = useState(false)
  const [isScenariosOpen, setIsScenariosOpen] = useState(false)
  const [lastSavedStrategy, setLastSavedStrategy] = useState({})
  const [results, setResults] = useState([])
  const [resultsRankEval, setResultsRankEval] = useState({})
  const [scenario, setScenario] = useState(null)
  const [scenarioOptions, setScenarioOptions] = useState([])
  const [scenarioSearchString, setScenarioSearchString] = useState('')
  const [sourceFilters, setSourceFilters] = useState([])
  const editorRef = useRef(null)

  ///  Strategy editing  ///////////////////////////////////////////////////////

  /**
   * Initialize form once loaded
   */
  useEffect(() => {
    if (!strategy)
      return
    setLastSavedStrategy(strategy)
    if (strategy.template?.source)
      setStrategyDraft(JSON.stringify(JSON.parse(strategy.template.source), null, 2))
  }, [strategy])

  /**
   * Extract params (formatted as Mustache variables) from a JSON string.
   */
  const RE_PARAMS = /{{\s*([\w.-]+)\s*}}/g
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

  const onSaveStrategy = async (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();

    try {
      JSON.parse(strategyDraft)
    } catch (e) {
      return addToast({
        color: 'danger',
        title: 'Failed to update strategy',
        text: `Your strategy isn't a valid JSON object.`
      })
    }

    // Prepare doc field updates
    const doc = {
      name: lastSavedStrategy.name,
      tags: lastSavedStrategy.tags,
      template: {
        lang: 'mustache',
        source: strategyDraft
      },
    }

    // Update doc
    let response
    try {
      setIsProcessing(true)
      response = await api.strategies_update(workspace._id, strategy._id, doc)
    } catch (e) {
      return addToast(api.errorToast(e, { title: 'Failed to update strategy' }))
    } finally {
      setIsProcessing(false)
    }
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    addToast(utils.toastDocCreateUpdateDelete('update', 'strategy', strategy._id))

    // Update doc in editor
    setLastSavedStrategy(prev => ({
      ...prev,
      ...doc,
      template: {
        ...prev.template,
        ...doc.template
      }
    }))
  }

  /**
   * Check if the strategy draft differs from the saved strategy.
   */
  const doesDraftDiffer = () => {
    try {
      return JSON.stringify(lastSavedStrategy.template?.source || '{}') == JSON.stringify(JSON.parse(strategyDraft || '{}'))
    } catch (e) {
      return undefined
    }
  }

  ////  Strategy testing  //////////////////////////////////////////////////////

  /**
   * Get index patterns and source filters from displays
   */
  useEffect(() => {
    if (!displays)
      return
    const _indexPatternMap = {}
    const _sourceFilters = {}
    displays.forEach((display) => {
      _indexPatternMap[display.index_pattern] = {
        display: display,
        regex: new RegExp(`^${display.index_pattern.replace(/\*/g, '.*')}$`)
      }
      display.fields?.forEach((field) => {
        _sourceFilters[field] = true
      })
    })
    setIndexPatternMap(_indexPatternMap)
    setSourceFilters(Object.keys(_sourceFilters))
  }, [displays])

  // Fetch scenarios immediately when opening the dropdown
  useEffect(() => {
    if (!workspace?._id || !isScenariosOpen)
      return
    onSearchScenarios(`*${scenarioSearchString}*`)
  }, [workspace?._id, isScenariosOpen])

  // Fetch scenarios with debounce when typing
  useEffect(() => {
    if (!workspace?._id || !isScenariosOpen)
      return
    const debounced = debounce(() => {
      onSearchScenarios(`*${scenarioSearchString}*`)
    }, 300)
    debounced()
    return () => debounced.cancel()
  }, [scenarioSearchString])

  useEffect(() => {
    if (!workspace?._id || !scenarioOptions)
      return
    for (const i in scenarioOptions) {
      if (scenarioOptions[i].checked) {
        setScenario(scenarioOptions[i])
        setScenarioSearchString(scenarioOptions[i].checked === 'on' ? scenarioOptions[i].label : '')
        break
      }
    }
  }, [scenarioOptions])

  // Add keyboard shortcuts to monaco editor
  useEffect(() => {
    const editor = editorRef.current
    if (!editor)
      return
    const saveCommand = editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => onSaveStrategy()
    )
    const testCommand = editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => onTestStrategy()
    )
    return () => { }
  }, [onSaveStrategy, onTestStrategy])

  ////  Event handlers  ////////////////////////////////////////////////////////

  // Add keyboard shortcuts to monaco editor
  const handleEditorMount = (editor) => {
    editorRef.current = editor
  }

  /**
   * Search for scenarios
   * 
   * TODO: Only find compatible scenarios that have the same params
   */
  const onSearchScenarios = async (text) => {
    try {
      setIsLoadingScenarios(true)
      const response = await api.scenarios_search(workspace._id, { text })
      const options = response.data.hits.hits.map((doc) => ({
        _id: doc._id,
        label: doc._source.name,
        values: doc._source.values,
      }))
      setScenarioOptions(options)
    } catch (e) {
      addToast(api.errorToast(e, { title: 'Failed to get scenarios' }))
    } finally {
      setIsLoadingScenarios(false)
    }
  }

  const applyParams = (template, scenarioValues) => {
    const rendered = template.replace(/{{\s*([\w.-]+)\s*}}/g, (_, key) => {
      return scenarioValues[key]
    })
    return JSON.parse(rendered)
  }

  /**
   * Handle testing strategy
   */
  const onTestStrategy = (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();

    // Verify that a scenario has been chosen
    let scenarioValues
    try {
      scenarioValues = scenario.values
    } catch (e) {
      return addToast({
        title: 'Failed to test strategy',
        color: 'warning',
        text: 'You must pick a scenario to test your strategy on. Choose a scenario from the search bar at the top of the right panel.'
      })
    }

    // Verify that the strategy can be populated with values from the scenario
    let strategyPopulated
    try {
      strategyPopulated = applyParams(strategyDraft, scenarioValues)
    } catch (e) {
      return addToast({
        title: `Can't test strategy`,
        color: 'warning',
        text: `Your strategy isn't a valid JSON object.`
      })
    }
    if (!strategyPopulated) {
      return addToast({
        title: `Can't test strategy`,
        color: 'warning',
        text: 'Failed to apply scenario values to strategy params.'
      })
    }

    // Submit API request(s)
    (async () => {

      // Prepare request body for search
      const body = {
        index_pattern: workspace.index_pattern,
        query: strategyPopulated
      }
      if (sourceFilters)
        body._source = { includes: sourceFilters }

      // Prepare request body for rank evaluation (if enabled)
      let evaluation
      if (isRankEvalEnabled) {
        evaluation = {
          "@meta": {
            "status": "pending",
            "created_at": new Date().toISOString(),
            "started_at": null,
            "stopped_at": null
          },
          "workspace_id": workspace._id,
          "task": {
            "metrics": ["ndcg", "precision", "recall"],
            "k": 10,
            "strategies": {
              "docs": [
                {
                  _id: strategy._id,
                  _source: {
                    name: lastSavedStrategy.name,
                    tags: lastSavedStrategy.tags,
                    params: extractParams(strategyDraft),
                    template: {
                      source: JSON.parse(strategyDraft)
                    }
                  }
                }
              ]
            },
            "scenarios": {
              "_ids": [scenario._id]
            }
          }
        }
      }

      // Submit API request(s)
      let responseSearch
      let responseRankEval
      try {
        setIsLoadingResults(true)
        const promises = [
          api.judgements_search(workspace._id, scenario._id, body),
          isRankEvalEnabled
            ? api.evaluations_run(workspace._id, evaluation)
            : Promise.resolve(null),
        ]
        const [response_search, response_rank_eval] = await Promise.all(promises)
        responseSearch = response_search
        responseRankEval = response_rank_eval

        // Handle API response
        setErrorContent(null)
        setHasSearched(true)
        setResults(responseSearch.data.hits.hits)
        setResultsRankEval(responseRankEval?.data || {})
      } catch (e) {
        if (responseSearch?.data?.error?.reason || responseRankEval?.data?.error?.reason) {
          setHasSearched(true)
          if (responseSearch?.data?.error?.reason)
            setErrorContent(responseSearch.data)
          if (responseRankEval?.data?.error?.reason)
            setErrorContent(responseRankEval.data)
        } else {
          return addToast(api.errorToast(e, { title: 'Failed to test strategy' }))
        }
      } finally {
        setIsLoadingResults(false)
      }
    })()
  }

  /**
   * Reset the form to the last saved strategy.
   */
  const resetForm = () => {
    setStrategyDraft(JSON.stringify(lastSavedStrategy.template.source, null, 2))
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderError = () => (
    <EuiCodeBlock isCopyable language='json' paddingSize='s'>
      {JSON.stringify(errorContent, null, 2)}
    </EuiCodeBlock>
  )

  const renderSelectScenarios = () => (
    <SelectScenario
      isLoading={isLoadingScenarios}
      isOpen={isScenariosOpen}
      options={scenarioOptions}
      placeholder={'Choose a scenario to test on...'}
      searchString={scenarioSearchString}
      setSearchString={setScenarioSearchString}
      setIsLoading={setIsLoadingScenarios}
      setIsOpen={setIsScenariosOpen}
      setOptions={setScenarioOptions}
    />
  )

  const renderResults = () => (<>
    {results.length > 0 &&
      <SearchResultsJudgements
        indexPatternMap={indexPatternMap}
        workspace={workspace}
        scenario={scenario}
        results={results}
        resultsPerRow={2}
        showScore={true}
      />
    }
    {hasSearched && results.length == 0 &&
      <p>No results.</p>
    }
  </>)

  const renderTestPanel = () => (
    <EuiPanel
      hasBorder={false}
      hasShadow={false}
      paddingSize='none'
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <EuiPanel color='transparent' grow={false} paddingSize='none'>
        <EuiFlexGroup gutterSize='m'>
          <EuiFlexItem grow>
            {renderSelectScenarios()}
          </EuiFlexItem>
          <EuiFlexItem grow={false}>
            <EuiButton
              color='primary'
              disabled={isProcessing || !scenario}
              iconType='search'
              onClick={onTestStrategy}
              type='submit'
            >
              Test
            </EuiButton>
          </EuiFlexItem>
        </EuiFlexGroup>
      </EuiPanel>
      <EuiSpacer size='m' />
      <EuiPanel
        color='transparent'
        hasBorder
        paddingSize='none'
        style={{
          display: 'flex',
          flex: 1,
          minHeight: 0,
          overflow: 'visible',
          position: 'relative',
        }}>
        {isLoadingResults &&
          <EuiProgress
            color='accent'
            size='s'
            style={{
              borderTopLeftRadius: '4px',
              borderTopRightRadius: '4px',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0
            }}
          />
        }
        <EuiPanel
          color='subdued'
          paddingSize='m'
          style={{
            opacity: isLoadingResults ? 0.5 : 1.0,
            overflow: 'scroll',
          }}
        >
          {errorContent ? renderError() : renderResults()}
        </EuiPanel>
      </EuiPanel>

      {/* Placeholder */}
      <div style={{ flexShrink: 0, height: '24px', margin: '5px 0 -10px 0' }}>
        <EuiPanel color='transparent' grow={false} hasBorder={false} hasShadow={false} paddingSize='xs'>
          <EuiFlexGroup gutterSize='m'>
            <EuiFlexItem grow={false}>
              <div onClick={() => setIsRankEvalEnabled(!isRankEvalEnabled)} style={{ cursor: 'pointer' }}>
                <EuiSwitch
                  checked={isRankEvalEnabled}
                  mini
                  onChange={() => setIsRankEvalEnabled(!isRankEvalEnabled)}
                />
                <EuiText size='xs' style={{ display: 'inline', fontSize: '11px' }}>
                  Rank Eval
                </EuiText>
              </div>
            </EuiFlexItem>
            {resultsRankEval?.summary &&
              <EuiFlexItem grow={false}>
                <div style={{ marginTop: '-2px' }}>
                  <EuiBadge color='hollow' size='s' style={{ display: 'inline-block' }}>
                    <small>
                      NDCG: <b>{resultsRankEval.summary.strategy_id[strategy._id]._total.metrics.ndcg.avg.toFixed(4)}</b>
                    </small>
                  </EuiBadge>
                  <EuiBadge color='hollow' size='s' style={{ display: 'inline-block' }}>
                    <small>
                      Precision: <b>{resultsRankEval.summary.strategy_id[strategy._id]._total.metrics.precision.avg.toFixed(4)}</b>
                    </small>
                  </EuiBadge>
                  <EuiBadge color='hollow' size='s' style={{ display: 'inline-block' }}>
                    <small>
                      Recall: <b>{resultsRankEval.summary.strategy_id[strategy._id]._total.metrics.recall.avg.toFixed(4)}</b>
                    </small>
                  </EuiBadge>
                </div>
              </EuiFlexItem>
            }
          </EuiFlexGroup>
        </EuiPanel>
      </div>
    </EuiPanel>
  )

  const renderEditor = () => {
    return (
      <Editor
        height='100%'
        language='json'
        onChange={(value, event) => setStrategyDraft(value)}
        onMount={handleEditorMount}
        options={{
          folding: true,
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

  const renderEditorPanel = () => (
    <EuiPanel
      hasBorder={false}
      hasShadow={false}
      paddingSize='none'
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <EuiPanel color='transparent' grow={false} paddingSize='none'>

        {/* Buttons */}
        <EuiFlexGroup gutterSize='m'>
          <EuiFlexItem grow={false}>
            <EuiButton
              color='primary'
              disabled={isProcessing || doesDraftDiffer()}
              fill
              onClick={onSaveStrategy}
              type='submit'
            >
              Save
            </EuiButton>
          </EuiFlexItem>
          <EuiFlexItem grow={false}>
            <EuiButton
              color="text"
              disabled={isProcessing || doesDraftDiffer()}
              onClick={resetForm}
            >
              Reset
            </EuiButton>
          </EuiFlexItem>
        </EuiFlexGroup>
      </EuiPanel>
      <EuiSpacer size='m' />

      {/* Editor */}
      <EuiPanel
        hasBorder
        paddingSize='none'
        style={{
          display: 'flex',
          flex: 1,
          minHeight: 0,
          opacity: isLoadingResults ? 0.5 : 1.0,
        }}
      >
        {renderEditor()}
      </EuiPanel>

      {/* Display keyboard shortcuts */}
      <div style={{ flexShrink: 0, height: '24px', margin: '5px 0 -10px 0' }}>
        <EuiPanel color='transparent' grow={false} hasBorder={false} hasShadow={false} paddingSize='xs'>
          <EuiFlexGroup gutterSize='m'>
            <EuiFlexItem grow={false}>
              <EuiIcon color='subdued' type='keyboard' style={{ margin: '-1px 10px 0 0' }} />
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiText size='xs'>
                <small>Save:<EuiCode transparentBackground>Ctrl/Cmd</EuiCode>+<EuiCode transparentBackground>S</EuiCode></small>
              </EuiText>
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiText size='xs'>
                <small>Test:<EuiCode transparentBackground>Ctrl/Cmd</EuiCode>+<EuiCode transparentBackground>Enter</EuiCode></small>
              </EuiText>
            </EuiFlexItem>
          </EuiFlexGroup>
        </EuiPanel>
      </div>
    </EuiPanel>
  )

  const renderSplitPanels = () => (
    <EuiPanel paddingSize='s' style={{ height: '100%' }}>
      <EuiResizableContainer direction='horizontal' style={{ height: '100%' }}>
        {(EuiResizablePanel, EuiResizableButton) => (
          <>
            {/* Editor panel */}
            <EuiResizablePanel initialSize={40} minSize='300px' paddingSize='s' style={{ overflow: 'visible' }}>
              <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none' style={{ height: '100%' }}>
                {renderEditorPanel()}
              </EuiPanel>
            </EuiResizablePanel>

            <EuiResizableButton />

            {/* Test panel */}
            <EuiResizablePanel initialSize={60} minSize='300px' paddingSize='s' style={{ overflow: 'visible' }}>
              <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none' style={{ height: '100%' }}>
                {renderTestPanel()}
              </EuiPanel>
            </EuiResizablePanel>
          </>
        )}
      </EuiResizableContainer>
    </EuiPanel>
  )

  const renderButtonHelp = () => (
    <EuiButton color='text' iconType='help' onClick={() => setShowHelp(!showHelp)}>
      Help
    </EuiButton>
  )

  return (
    <Page panelled={true} title={
      <EuiSkeletonTitle isLoading={!isReady} size='l'>
        {!strategy &&
          <>Not found</>
        }
        {!!strategy &&
          <>{strategy.name}</>
        }
      </EuiSkeletonTitle>
    } buttons={[renderButtonHelp()]}>
      {showHelp && <FlyoutHelp onClose={() => setShowHelp(false)} />}
      {renderSplitPanels()}
    </Page>
  )
}

export default StrategiesEdit