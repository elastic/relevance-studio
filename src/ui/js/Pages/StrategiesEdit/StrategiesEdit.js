import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import {
  EuiButton,
  EuiFlexGroup,
  EuiFlexItem,
  EuiForm,
  EuiFormRow,
  EuiHorizontalRule,
  EuiPanel,
  EuiResizableButton,
  EuiResizableContainer,
  EuiResizablePanel,
  EuiSkeletonText,
  EuiSkeletonTitle,
  EuiSpacer,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'
import FlyoutHelp from './FlyoutHelp'
import { Page } from '../../Layout'
import api from '../../api'
import utils from '../../utils'

const StrategiesEdit = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, darkMode } = useAppContext()
  const { project, isProjectReady } = useProjectContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [isLoadingStrategy, setIsLoadingStrategy] = useState(true)
  const [isProcessing, setIsProcessing] = useState(false)
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


  ////  Render  ////////////////////////////////////////////////////////////////

  const renderEditor = () => {
    return (
      <Editor
        height='100%'
        language='json'
        onChange={(value, event) => setStrategyDraft(value)}
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
        <EuiPanel color='transparent'>
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
        <EuiHorizontalRule margin='none' />
      </EuiPanel>
      <div style={{ flex: 1, display: 'flex' }}>
        {renderEditor()}
      </div>
    </EuiPanel>
  )

  const renderSplitPanels = () => (
    <EuiPanel paddingSize='s' style={{ height: '100%' }}>
      <EuiResizableContainer direction='horizontal' style={{ height: '100%' }}>
        {(EuiResizablePanel, EuiResizableButton) => (
          <>
            <EuiResizablePanel initialSize={50} minSize='300px' paddingSize='s' scrollable>
              <EuiPanel hasBorder hasShadow={false} paddingSize='none' style={{ height: '100%' }}>
                {renderEditorPanel()}
              </EuiPanel>
            </EuiResizablePanel>

            <EuiResizableButton />

            <EuiResizablePanel initialSize={50} minSize='300px' paddingSize='s' scrollable>
              <EuiPanel hasBorder hasShadow={false} paddingSize='m' style={{ height: '100%' }}>
                <div style={{ height: '100%', overflow: 'auto' }}>
                  {/* TODO */}
                </div>
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
      {/*
      <EuiFlexGroup alignItems='flexStart' style={{ height: 'calc(100vh - 135px)' }}>
        <EuiFlexItem grow={5}>
          {renderEditorPanel()}
        </EuiFlexItem>
      </EuiFlexGroup>
      */}
    </Page>
  )
}

export default StrategiesEdit