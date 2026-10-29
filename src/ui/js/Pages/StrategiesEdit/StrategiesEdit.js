/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import {
  EuiAccordion,
  EuiBadge,
  EuiTab,
  EuiTabs,
  EuiButton,
  EuiButtonEmpty,
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
  copyToClipboard,
} from '@elastic/eui'
import { debounce } from 'lodash'
import { useAppContext } from '../../Contexts/AppContext'
import { usePageResources, useResources, useAdditionalResources } from '../../Contexts/ResourceContext'
import { useDisplays } from '../../Hooks'
import {
  HyperparameterEditor,
  HyperparameterInputs,
  Page,
  SelectScenario,
  SearchResultsJudgements,
} from '../../Layout'
import FlyoutHelp from './FlyoutHelp'
import TabBenchmark from './TabBenchmark'
import api from '../../api'
import hp from '../../hyperparameters'
import utils from '../../utils'
import { getHistory } from '../../history'

const TEST_TABS = [
  { id: 'search', label: 'Search' },
  { id: 'benchmark', label: 'Benchmark' },
]

const StrategiesEdit = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const location = useLocation()
  const history = getHistory()
  const { addToast, darkMode } = useAppContext()
  const { workspace, strategy, displays } = usePageResources()
  useAdditionalResources(['displays'])
  const isReady = useResources().hasResources(['workspace', 'strategy', 'displays'])
  const { sourceFilters, resolveIndexToDisplay } = useDisplays(displays, workspace?.index_pattern)

  ////  State  /////////////////////////////////////////////////////////////////

  // Strategy editing
  const [isProcessing, setIsProcessing] = useState(false)
  const [params, setParams] = useState([])
  const [showHelp, setShowHelp] = useState(false)
  const [strategyDraft, setStrategyDraft] = useState('')
  const [hyperparameters, setHyperparameters] = useState([])
  const [isCopyingTemplate, setIsCopyingTemplate] = useState(false)
  const [hpInputs, setHpInputs] = useState({})
  const [hyperparametersOpen, setHyperparametersOpen] = useState(false)
  const [testTab, setTestTab] = useState('search')

  // Strategy testing
  const [errorContent, setErrorContent] = useState(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [initialScenarioLoaded, setInitialScenarioLoaded] = useState(false)
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
  const editorRef = useRef(null)
  const lastTestedHpKey = useRef(null)
  const monacoRef = useRef(null)

  // Helper to get URL params
  const getUrlParams = () => {
    const params = new URLSearchParams(location.search)
    return {
      scenario: params.get('scenario_id'),
    }
  }

  // Helper to update URL without adding to history
  const updateUrl = (newParams) => {
    const params = new URLSearchParams(location.search)
    Object.entries(newParams).forEach(([key, value]) => {
      if (value) {
        params.set(key, value)
      } else {
        params.delete(key)
      }
    })
    history.replace(`${location.pathname}?${params.toString()}`)
  }

  ///  Strategy editing  ///////////////////////////////////////////////////////

  /**
   * Initialize form once loaded
   */
  useEffect(() => {
    if (!strategy)
      return
    setLastSavedStrategy(strategy)
    if (strategy.template?.source)
      setStrategyDraft(utils.formatJsonWithMustache(strategy.template.source))
    setHyperparameters(structuredClone(strategy.hyperparameters || []))

    // Reset test results when switching strategies
    setResults([])
    setResultsRankEval({})
    setHasSearched(false)
    setErrorContent(null)
  }, [strategy])

  /**
   * Extract the scenario params (Mustache variables) from a JSON string.
   * Hyperparameter references ({{hp.*}}) aren't params, because scenarios
   * don't provide them.
   */
  const extractParams = (jsonString) => {
    const arr = hp.extractScenarioParams(jsonString)
    setParams(arr)
    return arr
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
      utils.formatJsonWithMustache(strategyDraft)
    } catch (e) {
      return addToast({
        color: 'danger',
        title: 'Failed to update strategy',
        text: `Your strategy isn't a valid JSON object.`
      })
    }

    // Hyperparameter definitions must match the template references
    if (validation.errors.length) {
      return addToast({
        color: 'danger',
        title: 'Failed to update strategy',
        text: validation.errors[0]
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
      hyperparameters: hp.definitionsForSave(hyperparameters),
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
    setHyperparameters(structuredClone(doc.hyperparameters))
  }

  /**
   * Check if the strategy draft is the same as the saved strategy. Returns
   * undefined when the draft isn't valid JSON.
   */
  const isDraftSaved = () => {
    try {
      return utils.formatJsonWithMustache(lastSavedStrategy.template?.source || '{}') == utils.formatJsonWithMustache(strategyDraft || '{}')
        && hp.sameDefinitions(lastSavedStrategy.hyperparameters || [], hyperparameters)
    } catch (e) {
      return undefined
    }
  }

  /**
   * Validate the hyperparameter definitions against the template draft.
   */
  const validation = hp.validateDefinitions(hyperparameters, strategyDraft)

  /**
   * The hyperparameter inputs of a search test. They start at the promoted
   * values and follow the definitions as the user edits them.
   */
  useEffect(() => {
    setHpInputs((prev) => hp.syncInputs(hyperparameters, prev))
  }, [hyperparameters])
  const hpParsed = hp.parseInputs(hyperparameters, hpInputs)
  const hpInputErrors = Object.values(hpParsed.errors)
  const hpValuesKey = JSON.stringify(hpParsed.values)

  /**
   * Copy the production template: the template with the hyperparameter
   * promoted values applied, ready to use in a search request.
   */
  const onCopyProductionTemplate = async () => {
    let response
    try {
      setIsCopyingTemplate(true)
      response = await api.strategies_render(workspace._id, {
        template: { source: strategyDraft },
        hyperparameters: hp.definitionsForSave(hyperparameters),
      })
    } catch (e) {
      return addToast(api.errorToast(e, { title: 'Failed to render the production template' }))
    } finally {
      setIsCopyingTemplate(false)
    }
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    copyToClipboard(response.data.source)
    addToast({
      color: 'success',
      iconType: 'check',
      title: 'Copied the production template',
      text: 'The template has the hyperparameter promoted values applied. Scenario params stay as Mustache variables.',
    })
  }

  ////  Strategy testing  //////////////////////////////////////////////////////

  // Fetch scenarios immediately when opening the dropdown, show all scenarios
  useEffect(() => {
    if (!workspace?._id || !isScenariosOpen)
      return
    onSearchScenarios(`**`)
  }, [workspace?._id, isScenariosOpen])

  // Fetch scenarios with debounce when typing (only while dropdown is open and user has typed something)
  useEffect(() => {
    if (!workspace?._id || !isScenariosOpen || scenarioSearchString === '')
      return
    const debounced = debounce(() => {
      onSearchScenarios(`*${scenarioSearchString}*`)
    }, 300)
    debounced()
    return () => debounced.cancel()
  }, [scenarioSearchString])

  // Match scenario from URL params on initial load, or use the first checked option
  useEffect(() => {
    if (!workspace?._id || !scenarioOptions || initialScenarioLoaded)
      return

    const urlParams = getUrlParams()

    // Check if we have a scenario from URL params
    if (urlParams.scenario) {
      for (const option of scenarioOptions) {
        if (option._id === urlParams.scenario) {
          option.checked = 'on'
          setScenario(option)
          setScenarioSearchString(option.label)
          setInitialScenarioLoaded(true)
          return
        }
      }
    }

    // Otherwise, use the first checked option
    for (const option of scenarioOptions) {
      if (option.checked) {
        setScenario(option)
        setScenarioSearchString(option.checked === 'on' ? option.label : '')
        setInitialScenarioLoaded(true)
        break
      }
    }
  }, [scenarioOptions])

  // Fetch scenarios on mount if URL has a scenario param
  useEffect(() => {
    if (!workspace?._id)
      return
    const urlParams = getUrlParams()
    if (urlParams.scenario && scenarioOptions.length === 0)
      onSearchScenarios(`**`)
  }, [workspace?._id, scenarioOptions.length])

  // Automatically test strategy when scenario changes
  useEffect(() => {
    if (!isReady || !scenario)
      return
    onTestStrategy()
  }, [isReady, scenario])

  // Automatically test strategy when the hyperparameter values change
  useEffect(() => {
    if (!isReady || !scenario || hpInputErrors.length || lastTestedHpKey.current === hpValuesKey)
      return
    const timer = setTimeout(() => onTestStrategy(), 500)
    return () => clearTimeout(timer)
  }, [hpValuesKey])

  // Add keyboard shortcuts to monaco editor
  useEffect(() => {
    const editor = editorRef.current
    const monaco = monacoRef.current
    if (!editor || !monaco)
      return
    const saveCommand = editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => onSaveStrategy()
    )
    const testCommand = editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => onTestStrategy()
    )
    return () => {
      // Monaco cleans up commands automatically on editor dispose,
      // so no manual dispose needed here.
    }
  }, [onSaveStrategy, onTestStrategy])

  ////  Event handlers  ////////////////////////////////////////////////////////

  // Add keyboard shortcuts to monaco editor
  const handleEditorMount = (editor, monaco) => {
    editorRef.current = editor
    monacoRef.current = monaco

    // keep indentation/braces, but don’t let the (JSON) formatter fight with {{ }}
    editor.updateOptions({
      autoIndent: 'advanced',
      formatOnPaste: false,
      formatOnType: false,
    })
  }

  const handleBeforeMount = (monaco) => {
    monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
      validate: false, // turn off JSON syntax validation since Mustache is used
      allowComments: true,
      schemas: [],
    })
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
      const selectedId = scenario?._id || getUrlParams().scenario
      const options = response.data.hits.hits.map((doc) => ({
        _id: doc._id,
        label: doc._source.name,
        values: doc._source.values,
        checked: (selectedId === doc._id) ? 'on' : undefined
      }))
      setScenarioOptions(options)
    } catch (e) {
      addToast(api.errorToast(e, { title: 'Failed to get scenarios' }))
    } finally {
      setIsLoadingScenarios(false)
    }
  }

  // Apply the hyperparameter values chosen for the test, then the scenario values
  const applyParams = (template, scenarioValues) =>
    hp.applyTemplate(template, scenarioValues, hpParsed.values)

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

    // Verify that every hyperparameter has a valid value
    if (hpInputErrors.length) {
      return addToast({
        title: `Can't test strategy`,
        color: 'warning',
        text: 'Enter a valid value for every hyperparameter.'
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
        text: /^No value for hyperparameter/.test(e.message)
          ? e.message
          : `Your strategy isn't a valid JSON object.`
      })
    }
    lastTestedHpKey.current = hpValuesKey
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

      // Prepare request body for the ad-hoc rank-eval run (if enabled)
      let run
      if (isRankEvalEnabled) {
        run = {
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
                      source: strategyDraft
                    },
                    hyperparameters: hp.definitionsForSave(hyperparameters),
                  }
                }
              ]
            },
            "hyperparameter_values": hpParsed.values,
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
            ? api.runs_run(workspace._id, run)
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
   * Open a scenario of a Benchmark tab run in the Search tab.
   */
  const onOpenScenario = ({ _id, name, values }) => {
    updateUrl({ scenario_id: _id })
    setScenario({ _id, label: name, values, checked: 'on' })
    setScenarioSearchString(name)
    setScenarioOptions((prev) => prev.map((option) => ({ ...option, checked: option._id === _id ? 'on' : undefined })))
    setTestTab('search')
  }

  /**
   * Load the values of a variant into the hyperparameter inputs of the Search tab.
   */
  const onLoadValues = (values) => {
    setHpInputs(hp.inputsFromValues(hyperparameters, values))
    setTestTab('search')
  }

  /**
   * Apply the values of a variant to the promoted values of the draft.
   */
  const onApplyValues = (values) => {
    setHyperparameters((prev) => prev.map((definition) => (
      values[definition.name] === undefined ? definition : { ...definition, promoted_value: values[definition.name] }
    )))
    addToast({
      color: 'success',
      iconType: 'check',
      title: 'Applied the values to the draft',
      text: 'The hyperparameters now promote these values. Save the strategy to keep them.',
    })
  }

  /**
   * Reset the form to the last saved strategy.
   */
  const resetForm = () => {
    setStrategyDraft(lastSavedStrategy.template.source, null, 2)
    setHyperparameters(structuredClone(lastSavedStrategy.hyperparameters || []))
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
      onChange={(changedOption) => {
        // Update URL, set active scenario, and restore the scenario name in the search field
        updateUrl({ scenario_id: changedOption._id })
        setScenario(changedOption.checked === 'on' ? changedOption : null)
        setScenarioSearchString(changedOption.checked === 'on' ? changedOption.label : '')
      }}
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
        resolveIndexToDisplay={resolveIndexToDisplay}
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

  const renderTestTabs = () => (
    <EuiTabs size='s' style={{ flexShrink: 0 }}>
      {TEST_TABS.map((tab) => (
        <EuiTab
          isSelected={testTab === tab.id}
          key={tab.id}
          onClick={() => setTestTab(tab.id)}
        >
          {tab.label}
        </EuiTab>
      ))}
    </EuiTabs>
  )

  const renderBenchmarkTab = () => (
    <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingTop: '12px' }}>
      <TabBenchmark
        definitionErrors={validation.errors}
        draft={{
          name: lastSavedStrategy.name,
          tags: lastSavedStrategy.tags,
          source: strategyDraft,
          hyperparameters,
        }}
        isDraftSaved={isDraftSaved()}
        onApplyValues={onApplyValues}
        onLoadValues={onLoadValues}
        onOpenScenario={onOpenScenario}
        saved={{
          name: lastSavedStrategy.name,
          tags: lastSavedStrategy.tags,
          source: lastSavedStrategy.template?.source || '',
          hyperparameters: lastSavedStrategy.hyperparameters || [],
        }}
        strategyId={strategy._id}
        workspace={workspace}
      />
    </div>
  )

  const renderTestPanel = () => (
    <EuiPanel
      hasBorder={false}
      hasShadow={false}
      paddingSize='none'
      style={{
        flex: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {renderTestTabs()}
      <div style={{ display: testTab === 'search' ? 'contents' : 'none' }}>
        {renderSearchTab()}
      </div>
      {strategy &&
        <div style={{ display: testTab === 'benchmark' ? 'contents' : 'none' }}>
          {renderBenchmarkTab()}
        </div>
      }
    </EuiPanel>
  )

  const renderSearchTab = () => (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', paddingTop: '12px' }}>
      <EuiPanel color='transparent' grow={false} paddingSize='none'>
        <EuiFlexGroup gutterSize='m' responsive={false}>
          <EuiFlexItem grow>
            {renderSelectScenarios()}
          </EuiFlexItem>
          <EuiFlexItem grow={false}>
            <EuiButton
              color='primary'
              disabled={isProcessing || !scenario || hpInputErrors.length > 0}
              iconType='search'
              onClick={onTestStrategy}
              type='submit'
            >
              Test
            </EuiButton>
          </EuiFlexItem>
        </EuiFlexGroup>
        <EuiSpacer size='s' />
        <HyperparameterInputs
          definitions={hyperparameters}
          idPrefix='editor-search-hp'
          inputs={hpInputs}
          onChange={setHpInputs}
          onReset={() => setHpInputs(hp.syncInputs(hyperparameters, {}))}
          parsed={hpParsed}
        />
      </EuiPanel>
      <EuiSpacer size='m' />
      <EuiPanel
        color='transparent'
        hasBorder
        paddingSize='none'
        style={{
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          minHeight: 0,
          overflow: 'hidden',
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
            flex: 1,
            minHeight: 0,
            opacity: isLoadingResults ? 0.5 : 1.0,
            overflowY: 'auto',
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
    </div>
  )

  const renderEditor = () => {
    return (
      <Editor
        beforeMount={handleBeforeMount}
        height='100%'
        language='json'
        onMount={handleEditorMount}
        onChange={(value) => setStrategyDraft(value)}
        options={{
          folding: true,
          fontSize: 12,
          formatOnPaste: false, // keep the formatter from mangling Mustache variables {{ }}
          formatOnType: false,
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

  const renderHyperparameters = () => (
    <div style={{ flexShrink: 0, marginTop: '8px' }}>
      <EuiAccordion
        buttonContent={
          <EuiText size='s'>
            Hyperparameters{' '}
            <EuiBadge color='hollow'><small>{hyperparameters.length}</small></EuiBadge>
            {validation.errors.length > 0 &&
              <EuiIcon color='danger' size='s' style={{ marginLeft: '8px' }} type='warning' />
            }
          </EuiText>
        }
        forceState={hyperparametersOpen ? 'open' : 'closed'}
        id='strategy-hyperparameters'
        onToggle={setHyperparametersOpen}
        paddingSize='s'
      >
        <div style={{ maxHeight: '38vh', overflowY: 'auto' }}>
          <HyperparameterEditor
            definitions={hyperparameters}
            onChange={setHyperparameters}
            source={strategyDraft}
            validation={validation}
          />
        </div>
      </EuiAccordion>
    </div>
  )

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
        <EuiFlexGroup gutterSize='m' responsive={false}>
          <EuiFlexItem grow={false}>
            <EuiButton
              color='primary'
              disabled={isProcessing || isDraftSaved()}
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
              disabled={isProcessing || isDraftSaved()}
              onClick={resetForm}
            >
              Reset
            </EuiButton>
          </EuiFlexItem>
          <EuiFlexItem grow />
          {(hyperparameters.length > 0) &&
            <EuiFlexItem grow={false}>
              <EuiButtonEmpty
                color='text'
                iconType='copyClipboard'
                isLoading={isCopyingTemplate}
                onClick={onCopyProductionTemplate}
                size='s'
              >
                Copy production template
              </EuiButtonEmpty>
            </EuiFlexItem>
          }
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

      {/* Hyperparameters */}
      {renderHyperparameters()}

      {/* Display keyboard shortcuts */}
      <div style={{ flexShrink: 0, height: '24px', margin: '5px 0 -10px 0' }}>
        <EuiPanel color='transparent' grow={false} hasBorder={false} hasShadow={false} paddingSize='xs'>
          <EuiFlexGroup gutterSize='m' responsive={false}>
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
    <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <EuiResizableContainer direction='horizontal' style={{ flex: 1, minHeight: 0 }}>
        {(EuiResizablePanel, EuiResizableButton) => (
          <>
            {/* Editor panel */}
            <EuiResizablePanel
              initialSize={50}
              minSize='300px'
              paddingSize='s'
              scrollable={false}
              style={{ display: 'flex', flexDirection: 'column' }}
            >
              <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none' style={{ flex: 1, minHeight: 0 }}>
                {renderEditorPanel()}
              </EuiPanel>
            </EuiResizablePanel>

            <EuiResizableButton />

            {/* Test panel */}
            <EuiResizablePanel
              initialSize={50}
              minSize='300px'
              paddingSize='s'
              scrollable={false}
              style={{ display: 'flex', flexDirection: 'column' }}
            >
              <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none' style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
                {renderTestPanel()}
              </EuiPanel>
            </EuiResizablePanel>
          </>
        )}
      </EuiResizableContainer>
    </div>
  )

  const renderButtonHelp = () => (
    <EuiButton color='text' iconType='help' onClick={() => setShowHelp(!showHelp)}>
      Help
    </EuiButton>
  )

  return (
    <Page paddingSize='none' title={
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
      <div style={{ height: 'calc(100vh - 180px)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {renderSplitPanels()}
      </div>
    </Page>
  )
}

export default StrategiesEdit