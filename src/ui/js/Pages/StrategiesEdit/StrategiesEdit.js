import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import {
  EuiButton,
  EuiCode,
  EuiCodeBlock,
  EuiFlexGroup,
  EuiFlexItem,
  EuiIcon,
  EuiPanel,
  EuiResizableContainer,
  EuiSkeletonTitle,
  EuiSpacer,
  EuiText,
  EuiTitle,
} from '@elastic/eui'
import { debounce } from 'lodash'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'
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
  const { project, isProjectReady } = useProjectContext()

  ////  State  /////////////////////////////////////////////////////////////////

  // Strategy editing
  const [isLoadingStrategy, setIsLoadingStrategy] = useState(true)
  const [isProcessing, setIsProcessing] = useState(false)
  const [params, setParams] = useState([])
  const [showHelp, setShowHelp] = useState(false)
  const [strategy, setStrategy] = useState({})
  const [strategyDraft, setStrategyDraft] = useState('')
  const [strategyId, setStrategyId] = useState(null)

  // Strategy testing
  const [displays, setDisplays] = useState({})
  const [errorContent, setErrorContent] = useState(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [indexPatternRegexes, setIndexPatternRegexes] = useState({})
  const [isLoadingDisplays, setIsLoadingDisplays] = useState(false)
  const [isLoadingScenarios, setIsLoadingScenarios] = useState(false)
  const [isLoadingResults, setIsLoadingResults] = useState(false)
  const [isScenariosOpen, setIsScenariosOpen] = useState(false)
  const [results, setResults] = useState([])
  const [scenario, setScenario] = useState(null)
  const [scenarioOptions, setScenarioOptions] = useState([])
  const [scenarioSearchString, setScenarioSearchString] = useState('')
  const [sourceFilters, setSourceFilters] = useState([])
  const editorRef = useRef(null)

  ///  Strategy editing  ///////////////////////////////////////////////////////

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
        setIsLoadingStrategy(true)
        response = await api.strategies_get(project._id, strategyId)
      } catch (e) {
        return addToast(api.errorToast(e, { title: 'Failed to get strategy' }))
      } finally {
        setIsLoadingStrategy(false)
      }
      // Handle API response
      setStrategy(response.data._source)
    })()
  }, [project, strategyId])

  /**
   * Initialize strategy once loaded
   */
  useEffect(() => {
    if (!strategy?.template)
      return
    setStrategyDraft(JSON.stringify(strategy.template.source, null, 2))
  }, [strategy])

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

  const onSaveStrategy = async (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();

    // Prepare doc field updates
    const doc = {
      name: strategy.name,
      tags: strategy.tags,
      template: {
        source: JSON.parse(strategyDraft)
      },
    }

    // Update doc
    let response
    try {
      setIsProcessing(true)
      response = await api.strategies_update(project._id, strategyId, doc)
    } catch (e) {
      return addToast(api.errorToast(e, { title: 'Failed to update strategy' }))
    } finally {
      setIsProcessing(false)
    }
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    addToast(utils.toastDocCreateUpdateDelete('update', 'strategy', strategyId))

    // Update doc in editor
    setStrategy(prev => ({
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
      return JSON.stringify(strategy.template?.source || '{}') == JSON.stringify(JSON.parse(strategyDraft || '{}'))
    } catch (e) {
      return undefined
    }
  }

  ////  Strategy testing  //////////////////////////////////////////////////////

  /**
   * Get displays for project
   */
  useEffect(() => {
    if (!project?._id)
      return
    (async () => {

      // Submit API request
      let response
      try {
        setIsLoadingDisplays(true)
        response = await api.displays_search(project._id, { text: '*' })
      } catch (e) {
        return addToast(api.errorToast(e, { title: 'Failed to get displays' }))
      } finally {
        setIsLoadingDisplays(false)
      }

      // Handle API response
      const _displays = {}
      const _fields = {}
      const _indexPatternsRegexes = {}
      response.data.hits.hits?.forEach((doc) => {
        _displays[doc._source.index_pattern] = doc._source
        doc._source.fields?.forEach((field) => {
          _fields[field] = true
        })
      })
      for (var index_pattern in _displays) {
        const re = new RegExp(`^${index_pattern.replace(/\*/g, '.*')}$`)
        _indexPatternsRegexes[index_pattern] = re
      }
      setDisplays(_displays)
      setIndexPatternRegexes(_indexPatternsRegexes)
      setSourceFilters(Object.keys(_fields))
    })()
  }, [project])

  // Fetch scenarios immediately when opening the dropdown
  useEffect(() => {
    if (!project?._id || !isScenariosOpen)
      return
    onSearchScenarios(`*${scenarioSearchString}*`)
  }, [project?._id, isScenariosOpen])

  // Fetch scenarios with debounce when typing
  useEffect(() => {
    if (!project?._id || !isScenariosOpen)
      return
    const debounced = debounce(() => {
      onSearchScenarios(`*${scenarioSearchString}*`)
    }, 300)
    debounced()
    return () => debounced.cancel()
  }, [scenarioSearchString])

  useEffect(() => {
    if (!project?._id || !scenarioOptions)
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
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => onSubmitTest()
    )
    return () => { }
  }, [onSaveStrategy, onSubmitTest])

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
      const response = await api.scenarios_search(project._id, { text })
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
    const rendered = template.replace(/{{\s*([\w.]+)\s*}}/g, (_, key) => {
      return scenarioValues[key]
    })
    return JSON.parse(rendered)
  }

  /**
   * Handle search bar submission
   */
  const onSubmitTest = (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();
    let rendered
    let scenarios
    try {
      scenarios = scenario.values
    } catch (e) {
      return addToast({
        title: `Can't test strategy`,
        color: 'warning',
        text: (
          <EuiText size='xs'>
            <p>
              <EuiTitle size='xxs'>
                <EuiText style={{ fontWeight: 500, marginBottom: '2px' }}>
                  No scenario chosen
                </EuiText>
              </EuiTitle>
              You must pick a scenario to test your strategy on. Choose a scenario from the search bar at the top of the right panel.
            </p>
          </EuiText>
        )
      })
    }
    try {
      rendered = applyParams(strategyDraft, scenarios)
    } catch (e) {
      return addToast({
        title: `Can't test strategy`,
        color: 'warning',
        text: (
          <EuiText size='xs'>
            <p>
              <EuiTitle size='xxs'>
                <EuiText style={{ fontWeight: 500, marginBottom: '2px' }}>
                  Invalid JSON
                </EuiText>
              </EuiTitle>
              Your strategy isn't a valid JSON object.
            </p>
          </EuiText>
        )
      })
    }
    if (!rendered) {
      return addToast({
        title: `Can't test strategy`,
        color: 'warning',
        text: (
          <EuiText size='xs'>
            Failed to render strategy
          </EuiText>
        )
      })
    }
    (async () => {

      // Submit API request
      const body = {
        index_pattern: project.index_pattern,
        query: rendered
      }
      if (sourceFilters)
        body._source = { includes: sourceFilters }
      let response
      try {
        setIsLoadingResults(true)
        response = await api.judgements_search(project._id, scenario._id, body)
      } catch (e) {
        if (e.response.data?.error?.reason) {
          setHasSearched(true)
          return setErrorContent(e.response.data)
        }
        return addToast(api.errorToast(e, { title: 'Failed to test strategy' }))
      } finally {
        setIsLoadingResults(false)
      }

      // Handle API response
      setErrorContent(null)
      setHasSearched(true)
      setResults(response.data.hits.hits)
    })()
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
        displays={displays}
        indexPatternRegexes={indexPatternRegexes}
        project={project}
        scenario={scenario}
        results={results}
        resultsPerRow={2}
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
              iconType='play'
              onClick={onSubmitTest}
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
          height: '100%',
          overflow: 'hidden'
        }}>
        <EuiPanel
          color='subdued'
          paddingSize='m'
          style={{
            opacity: isLoadingResults ? 0.5 : 1.0,
            overflow: 'scroll'
          }}
        >
          {errorContent ? renderError() : renderResults()}
        </EuiPanel>
      </EuiPanel>

      {/* Placeholder */}
      <div style={{ flexShrink: 0, height: '24px', margin: '5px 0 -10px 0' }}>
        {/* TODO */}
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
              onClick={() => {
                setStrategyDraft(JSON.stringify(strategy.template.source, null, 2));
              }}
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
            <EuiResizablePanel initialSize={50} minSize='300px' paddingSize='s'>
              <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none' style={{ height: '100%' }}>
                {renderEditorPanel()}
              </EuiPanel>
            </EuiResizablePanel>

            <EuiResizableButton />

            {/* Test panel */}
            <EuiResizablePanel initialSize={50} minSize='300px' paddingSize='s'>
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
      <EuiSkeletonTitle isLoading={!isProjectReady || isLoadingStrategy} size='l'>
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