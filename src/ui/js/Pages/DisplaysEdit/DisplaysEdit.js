/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useRef, useState } from 'react'
import {
  EuiButton,
  EuiFieldSearch,
  EuiFieldText,
  EuiFlexGroup,
  EuiFlexItem,
  EuiForm,
  EuiFormRow,
  EuiPanel,
  EuiSpacer,
  EuiSkeletonText,
  EuiSkeletonTitle,
  EuiToolTip,
} from '@elastic/eui'
import Editor from '@monaco-editor/react'
import {
  IconBoxAlignLeftFilled,
  IconBoxAlignTopLeftFilled,
  IconBoxAlignTopRightFilled,
  IconBoxAlignRightFilled,
} from '@tabler/icons-react'
import { useAppContext } from '../../Contexts/AppContext'
import { usePageResources, useResources } from '../../Contexts/ResourceContext'
import { DocCard, Page } from '../../Layout'
import api from '../../api'
import utils from '../../utils'

const DisplaysEdit = () => {

  ////  Context  ///////////////////////////////////////////////////////////////
  
  const { addToast, darkMode } = useAppContext()
  const { workspace, display } = usePageResources()
  const isReady = useResources().hasResources(['workspace', 'display'])

  ////  State  /////////////////////////////////////////////////////////////////

  const [indices, setIndices] = useState([])
  const [isLoadingIndices, setIsLoadingIndices] = useState(true)
  const [isLoadingDocById, setIsLoadingDocById] = useState(false)
  const [isLoadingDocRandom, setIsLoadingDocRandom] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [lastSavedDisplay, setLastSavedDisplay] = useState({})
  const [mustacheVariables, setMustacheVariables] = useState(false)
  const [queryString, setQueryString] = useState('')
  const [sampleDoc, setSampleDoc] = useState()
  const [templateBodyDraft, setTemplateBodyDraft] = useState('')
  const [templateImagePosition, setTemplateImagePosition] = useState('top-left')
  const [templateImageUrl, setTemplateImageUrl] = useState('')
  const mustacheVariablesRef = useRef(mustacheVariablesRef)


  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Get indices when workspace is ready
   */
  useEffect(() => {
    if (!isReady)
      return
    (async () => {
      let response
      try {
        setIsLoadingIndices(true)
        response = await api.content_mappings_browse(workspace.index_pattern)
      } catch (e) {
        return addToast(api.errorToast(e, { title: 'Failed to get indices' }))
      } finally {
        setIsLoadingIndices(false)
      }
      setIndices(response.data)
    })()
  }, [isReady])

  /**
   * Initialize form once loaded
   */
  useEffect(() => {
    if (!display)
      return
    setLastSavedDisplay(display)
    if (display.template?.body)
      setTemplateBodyDraft(display.template.body)
    if (display.template?.image?.position)
      setTemplateImagePosition(display.template.image.position)
    if (display.template?.image?.url)
      setTemplateImageUrl(display.template.image.url)
    if (!sampleDoc)
      onGetDocRandom()
  }, [display])

  /**
   * Create mustache variables from index fields
   */
  useEffect(() => {
    if (!indices)
      return
    const _mustacheVariables = []
    for (const i in indices)
      for (const field in indices[i].fields)
        _mustacheVariables.push(field)
    setMustacheVariables(_mustacheVariables)
  }, [indices])

  useEffect(() => {
    mustacheVariablesRef.current = mustacheVariables
  }, [mustacheVariables])

  const handleEditorMount = (editor, monaco) => {
    monaco.languages.registerCompletionItemProvider('markdown', {
      triggerCharacters: ['{', ' '],
      provideCompletionItems: (model, position) => {
        const lineContent = model.getLineContent(position.lineNumber)
        const textUntilPosition = lineContent.slice(0, position.column - 1)

        // Match `{{`, optional whitespace, and a partial variable name
        const mustacheMatch = textUntilPosition.match(/{{\s*([\w.-]*)$/)
        if (!mustacheMatch)
          return { suggestions: [] }
        const currentPrefix = mustacheMatch[1]
        const suggestions = mustacheVariablesRef.current
          .filter((name) => name.startsWith(currentPrefix))
          .map((name) => ({
            label: name,
            kind: monaco.languages.CompletionItemKind.Variable,
            insertText: name,
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column - currentPrefix.length,
              endLineNumber: position.lineNumber,
              endColumn: position.column,
            },
          }))

        return { suggestions }
      },
    })
  }

  const onSaveDisplay = async (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();

    // Prepare doc field updates
    const doc = {
      index_pattern: lastSavedDisplay.index_pattern,
      template: {
        body: templateBodyDraft,
        image: {
          position: templateImagePosition,
          url: templateImageUrl,
        }
      }
    }

    // Update doc
    let response
    try {
      setIsProcessing(true)
      response = await api.displays_update(workspace._id, display._id, doc)
    } catch (e) {
      return addToast(api.errorToast(e, { title: `Failed to update display` }))
    } finally {
      setIsProcessing(false)
    }
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    addToast(utils.toastDocCreateUpdateDelete('update', 'display', display._id))

    // Update doc in editor
    setLastSavedDisplay(prev => ({
      ...prev,
      ...doc,
      template: {
        ...prev.template,
        ...doc.template
      }
    }))
  }

  const onGetDocRandom = async () => {
    if (!display?.index_pattern)
      return
    const body = {
      query: { function_score: { random_score: {} } },
      size: 1
    }
    // Submit API request
    let response
    try {
      setIsLoadingDocRandom(true)
      response = await api.content_search(display.index_pattern, body)
    } catch (e) {
      return addToast(api.errorToast(e, { title: 'Failed to get doc' }))
    } finally {
      setIsLoadingDocRandom(false)
    }
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    // Handle API response
    setSampleDoc((response?.data?.hits?.hits || [])[0])
    setQueryString('')
  }

  const onGetDocById = async () => {
    if (!display?.index_pattern)
      return
    const body = {
      query: { ids: { values: [queryString] } },
      size: 1
    }
    // Submit API request
    let response
    try {
      setIsLoadingDocById(true)
      response = await api.content_search(display.index_pattern, body)
    } catch (e) {
      return addToast(api.errorToast(e, { title: 'Failed to get doc' }))
    } finally {
      setIsLoadingDocById(false)
    }
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    // Handle API response
    setSampleDoc((response?.data?.hits?.hits || [])[0])
  }

  /**
   * Check if the draft template differs from the saved template.
   */
  const doesDraftDiffer = () => {
    if (lastSavedDisplay?.template?.image?.position != templateImagePosition)
      return true
    if (lastSavedDisplay?.template?.image?.url != templateImageUrl)
      return true
    if (lastSavedDisplay?.template?.body != templateBodyDraft)
      return true
    return false
  }

  /**
   * Reset the form to the last saved display.
   */
  const resetForm = () => {
    setTemplateBodyDraft(lastSavedDisplay.template.body)
    setTemplateImagePosition(lastSavedDisplay.template.image.position)
    setTemplateImageUrl(lastSavedDisplay.template.image.url)
  }


  ////  Render  ////////////////////////////////////////////////////////////////

  const renderEditor = () => {
    return (
      <Editor
        defaultLanguage='markdown'
        height='100%'
        onChange={(value, event) => setTemplateBodyDraft(value)}
        onMount={handleEditorMount}
        options={{
          folding: false,
          fontSize: 12,
          glyphMargin: false,
          insertSpaces: true,
          lineNumbers: 'false',
          lineNumbersMinChars: 0,
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
        value={templateBodyDraft}
      />
    )
  }

  return (
    <Page panelled={true} title={
      <EuiSkeletonTitle isLoading={!isReady} size='l'>
        {!display &&
          <>Not found</>
        }
        {!!display &&
          <>Edit display</>
        }
      </EuiSkeletonTitle>
    }>
      <EuiFlexGroup alignItems='flexStart'>

        {/* Editor */}
        <EuiFlexItem grow={5}>
          <EuiPanel paddingSize='m'>

            {/* Editor controls */}
            <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none'>
              <EuiForm>

                {/* Buttons */}
                <EuiFlexGroup gutterSize='m'>
                  <EuiFlexItem grow={false}>
                    <EuiButton
                      color='primary'
                      disabled={isProcessing || !doesDraftDiffer()}
                      fill
                      onClick={onSaveDisplay}
                      type='submit'
                    >
                      Save
                    </EuiButton>
                  </EuiFlexItem>
                  <EuiFlexItem grow={false}>
                    <EuiButton
                      color='text'
                      disabled={isProcessing || !doesDraftDiffer()}
                      onClick={resetForm}
                    >
                      Reset
                    </EuiButton>
                  </EuiFlexItem>
                </EuiFlexGroup>
                <EuiSpacer size='m' />

                {/* Editor */}
                <EuiFormRow fullWidth label='Markdown editor'>
                  <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none'>
                    <EuiSkeletonText lines={21} isLoading={!isReady}>
                      <div style={{ height: 'calc(100vh - 362px)' }}>
                        <EuiPanel
                          hasBorder
                          paddingSize='none'
                          style={{
                            position: 'absolute',
                            top: '0',
                            bottom: '0',
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

                {/* Image settings */}
                <EuiFormRow fullWidth>
                  <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none'>

                    {/* Image URL */}
                    <EuiFieldText
                      aria-label='Image URL'
                      compressed
                      fullWidth
                      onChange={(e) => setTemplateImageUrl(e.target.value)}
                      placeholder='http://my-image-server/{{ image.path }}'
                      prepend='Image URL'
                      value={templateImageUrl}
                    />
                    <EuiSpacer size='xs' />

                    {/* Image position */}
                    {/*<EuiToolTip content='Align left'>
                    <EuiButton
                      color='text'
                      fill={imagePosition == 'left' ? true : false}
                      onClick={() => setImagePosition('left')}
                      size='s'
                      style={{ minWidth: '16px', padding: '8px', borderBottomRightRadius: '0', borderTopRightRadius: '0' }}
                    >
                      <IconBoxAlignLeftFilled stroke={1.5} size={16} />
                    </EuiButton>
                  </EuiToolTip>*/}
                    <EuiToolTip content='Align top left'>
                      <EuiButton
                        color='text'
                        fill={templateImagePosition == 'top-left' ? true : false}
                        onClick={() => setTemplateImagePosition('top-left')}
                        size='s'
                        style={{ minWidth: '16px', padding: '8px', /*borderLeft: '0', borderRadius: '0'*/ borderBottomRightRadius: '0', borderTopRightRadius: '0' }}
                      >
                        <IconBoxAlignTopLeftFilled stroke={1.5} size={16} />
                      </EuiButton>
                    </EuiToolTip>
                    <EuiToolTip content='Align top right'>
                      <EuiButton
                        color='text'
                        fill={templateImagePosition == 'top-right' ? true : false}
                        onClick={() => setTemplateImagePosition('top-right')}
                        size='s'
                        style={{ minWidth: '16px', padding: '8px', borderLeft: '0', /*borderRadius: '0'*/ borderBottomLeftRadius: '0', borderTopLeftRadius: '0' }}
                      >
                        <IconBoxAlignTopRightFilled stroke={1.5} size={16} />
                      </EuiButton>
                    </EuiToolTip>
                    {/*<EuiToolTip content='Align right'>
                    <EuiButton
                      color='text'
                      fill={imagePosition == 'right' ? true : false}
                      onClick={() => setImagePosition('right')}
                      size='s'
                      style={{ minWidth: '16px', padding: '8px', borderLeft: '0', borderBottomLeftRadius: '0', borderTopLeftRadius: '0' }}
                    >
                      <IconBoxAlignRightFilled stroke={1.5} size={16} />
                    </EuiButton>
                  </EuiToolTip>*/}
                  </EuiPanel>
                </EuiFormRow>

              </EuiForm>
            </EuiPanel>
          </EuiPanel>
        </EuiFlexItem>

        {/* Output */}
        <EuiFlexItem grow={5}>

          {/* Search bar */}
          <EuiFlexGroup gutterSize='s'>
            <EuiFlexItem grow={false}>
              <EuiButton
                disabled={!indices || isLoadingDocById || isLoadingDocRandom}
                iconType='refresh'
                isLoading={isLoadingDocRandom}
                onClick={onGetDocRandom}
              >
                Random doc
              </EuiButton>
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiFieldSearch
                disabled={!indices || isLoadingDocById || isLoadingDocRandom}
                fullWidth
                isLoading={isLoadingDocById}
                placeholder='...or doc _id'
                value={queryString}
                onChange={(e) => setQueryString(e.target.value)}
                onSearch={onGetDocById}
              />
            </EuiFlexItem>
          </EuiFlexGroup>
          <EuiSpacer size='l' />

          {/* Body */}
          {sampleDoc &&
            <EuiPanel color='transparent' paddingSize='none' style={{
              opacity: isLoadingDocById || isLoadingDocRandom ? 0.5 : 1.0
            }}>
              <EuiFormRow fullWidth label='Example (large)'>
                <EuiFlexGroup>
                  <EuiFlexItem grow={10}>
                    <DocCard doc={sampleDoc} body={templateBodyDraft} imagePosition={templateImagePosition} imageUrl={templateImageUrl} />
                  </EuiFlexItem>
                </EuiFlexGroup>
              </EuiFormRow>
              <EuiSpacer size='m' />
              <EuiFormRow fullWidth label='Example (small)'>
                <EuiFlexGroup>
                  <EuiFlexItem grow={5}>
                    <DocCard doc={sampleDoc} body={templateBodyDraft} imagePosition={templateImagePosition} imageUrl={templateImageUrl} />
                  </EuiFlexItem>
                  <EuiFlexItem grow={5}>
                  </EuiFlexItem>
                </EuiFlexGroup>
              </EuiFormRow>
            </EuiPanel>
          }

        </EuiFlexItem>
      </EuiFlexGroup>
    </Page>
  )
}

export default DisplaysEdit