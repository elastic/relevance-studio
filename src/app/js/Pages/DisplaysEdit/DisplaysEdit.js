import React, { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
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
  IconBoxAlignRightFilled
} from '@tabler/icons-react'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'
import { Page } from '../../Layout'
import DocCard from '../Displays/DocCard'
import api from '../../api'

const DisplaysEdit = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, darkMode } = useAppContext()
  const {
    project,
    isProjectReady,
    isLoadingDisplay,
    isProcessingDisplay,
    loadAssets,
    displays,
    indices,
    updateDisplay
  } = useProjectContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [isLoadingDocById, setIsLoadingDocById] = useState(false)
  const [isLoadingDocRandom, setIsLoadingDocRandom] = useState(false)
  const [mustacheVariables, setMustacheVariables] = useState(false)
  const [queryString, setQueryString] = useState('')
  const [sampleDoc, setSampleDoc] = useState()
  const [templateBodyDraft, setTemplateBodyDraft] = useState('')
  const [templateImagePosition, setTemplateImagePosition] = useState('top-left')
  const [templateImageUrl, setTemplateImageUrl] = useState('')
  const mustacheVariablesRef = useRef(mustacheVariablesRef)

  /**
   * Parse displayId from URL path
   */
  const { display_id: displayId } = useParams()

  /**
   * Load (or reload) any needed assets when project is ready.
   */
  useEffect(() => {
    if (isProjectReady)
      loadAssets({ indices: true, displays: true })
  }, [project?._id])

  /**
   * Reference the display in the project state when editing
   */
  const display = displays?.[displayId]

  /**
   * Initialize display once loaded
   */
  useEffect(() => {
    if (!display)
      return
    if (display.template?.body)
      setTemplateBodyDraft(display.template.body)
    if (display.template?.image?.position)
      setTemplateImagePosition(display.template.image.position)
    if (display.template?.image?.url)
      setTemplateImageUrl(display.template.image.url)
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
        const mustacheMatch = textUntilPosition.match(/{{\s*([\w.]*)$/)
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
    e.preventDefault();
    const newDoc = {
      _id: display._id,
      index_pattern: display.index_pattern,
      template: {
        body: templateBodyDraft
      }
    }
    if (templateImagePosition || templateImageUrl)
      newDoc.template.image = {}
    if (templateImagePosition)
      newDoc.template.image.position = templateImagePosition
    if (templateImageUrl)
      newDoc.template.image.url = templateImageUrl
    await updateDisplay(newDoc)
  }

  const onGetDocRandom = () => {
    (async () => {
      const body = {
        query: { function_score: { random_score: {} } },
        size: 1
      }

      // Submit API request
      let response
      try {
        setIsLoadingDocRandom(true)
        response = await api.search(display.index_pattern, body)
      } catch (error) {
        return addToast(api.errorToast(error, { title: 'Failed to get doc' }))
      } finally {
        setIsLoadingDocRandom(false)
      }

      // Handle API response
      setSampleDoc(response.data.hits.hits[0])
      setQueryString('')
    })()
  }

  const onGetDocById = () => {
    (async () => {
      const body = {
        query: { ids: { values: [queryString] } },
        size: 1
      }

      // Submit API request
      let response
      try {
        setIsLoadingDocById(true)
        response = await api.search(display.index_pattern, body)
      } catch (error) {
        return addToast(api.errorToast(error, { title: 'Failed to get doc' }))
      } finally {
        setIsLoadingDocById(false)
      }

      // Handle API response
      setSampleDoc(response.data.hits.hits[0])
    })()
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

  /**
   * Check if the draft template differs from the saved template.
   */
  const doesDraftDiffer = () => {
    if (display?.template?.image?.position != templateImagePosition)
      return true
    if (display?.template?.image?.url != templateImageUrl)
      return true
    if (display?.template?.body != templateBodyDraft)
      return true
    return false
  }

  return (<>
    <Page title={
      <EuiSkeletonTitle isLoading={!isProjectReady || isLoadingDisplay} size='l'>
        {!display &&
          <>Not found</>
        }
        {!!display &&
          <>Edit display</>
        }
      </EuiSkeletonTitle>
    }>
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
                    disabled={isProcessingDisplay || !doesDraftDiffer()}
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
                    disabled={isProcessingDisplay || !doesDraftDiffer()}
                    onClick={() => { setTemplateBodyDraft(display.template.body) }}
                  >
                    Reset
                  </EuiButton>
                </EuiFlexItem>
              </EuiFlexGroup>
              <EuiSpacer size='m' />

              {/* Editor */}
              <EuiFormRow fullWidth label='Markdown editor'>
                <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none'>
                  <EuiSkeletonText lines={21} isLoading={!isProjectReady}>
                    <div style={{ height: 'calc(100vh - 300px)' }}>
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
          <EuiSkeletonText lines={10} isLoading={isLoadingDocById || isLoadingDocRandom}>
            {sampleDoc &&
              <EuiFormRow fullWidth label='Example (large)'>
                <EuiFlexGroup>
                  <EuiFlexItem grow={10}>
                    <DocCard doc={sampleDoc} body={templateBodyDraft} imagePosition={templateImagePosition} imageUrl={templateImageUrl} />
                  </EuiFlexItem>
                </EuiFlexGroup>
              </EuiFormRow>
            }
          </EuiSkeletonText>
          <EuiSpacer size='m' />
          <EuiSkeletonText lines={10} isLoading={isLoadingDocById || isLoadingDocRandom}>
            {sampleDoc &&
              <EuiFormRow fullWidth label='Example (small)'>
                <EuiFlexGroup>
                  <EuiFlexItem grow={5}>
                    <DocCard doc={sampleDoc} body={templateBodyDraft} imagePosition={templateImagePosition} imageUrl={templateImageUrl} />
                  </EuiFlexItem>
                  <EuiFlexItem grow={5}>
                  </EuiFlexItem>
                </EuiFlexGroup>
              </EuiFormRow>
            }
          </EuiSkeletonText>

        </EuiFlexItem>
      </EuiFlexGroup>
    </Page>
  </>)
}

export default DisplaysEdit