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
import api from '../../api'
import utils from '../../utils'
import DocCard from '../Displays/DocCard'
import { Page } from '../../Layout'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'

const DisplaysEdit = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, darkMode } = useAppContext()
  const { project, loadingProject } = useProjectContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [bodyDraft, setBodyDraft] = useState('')
  const [display, setDisplay] = useState({})
  const [displayId, setDisplayId] = useState(null)
  const [doc, setDoc] = useState()
  const [indices, setIndices] = useState({})
  const [imagePosition, setImagePosition] = useState('top-left')
  const [imageUrl, setImageUrl] = useState('')
  const [loadingDisplay, setLoadingDisplay] = useState(true)
  const [loadingDocById, setLoadingDocById] = useState(false)
  const [loadingDocRandom, setLoadingDocRandom] = useState(false)
  const [loadingIndices, setLoadingIndices] = useState(false)
  const [mustacheVariables, setMustacheVariables] = useState(false)
  const [queryString, setQueryString] = useState('')
  const mustacheVariablesRef = useRef(mustacheVariablesRef)

  /**
   * Parse displayId from URL path
   */
  const { display_id } = useParams()
  useEffect(() => setDisplayId(display_id), [display_id])

  /**
   * Get display on load
   */
  useEffect(() => {
    if (!project?._id || displayId == null)
      return
    (async () => {

      // Submit API request
      let response
      try {
        setLoadingDisplay(true)
        response = await api.get_display(project._id, displayId)
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to get display' }))
      } finally {
        setLoadingDisplay(false)
      }

      // Handle API response
      setDisplay(response.data._source)
    })()
  }, [project, displayId])

  /**
   * Get displays on load
   */
  useEffect(() => {
    if (!display.index_pattern)
      return
    onGetDocRandom()
  }, [display.index_pattern])

  /**
   * Get indices for display
   */
  useEffect(() => {
    if (!display.index_pattern)
      return
    (async () => {

      // Submit API request
      let response
      try {
        setLoadingIndices(true)
        response = await api.get_indices(display.index_pattern)
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to get indices' }))
      } finally {
        setLoadingIndices(false)
      }

      // Handle API response
      setIndices(response.data)
    })()
  }, [display])

  /**
   * Update template
   */
  useEffect(() => {
    if (!display.template)
      return
    if (display.template.body)
      setBodyDraft(display.template.body)
    if (display.template.image?.position)
      setImagePosition(display.template.image.position)
    if (display.template.image?.url)
      setImageUrl(display.template.image.url)
  }, [display.template])

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

  const onSaveDisplay = (e) => {
    e.preventDefault();
    (async () => {

      // Submit API request
      const doc = {
        index_pattern: display.index_pattern,
        template: {
          body: bodyDraft
        }
      }
      if (imagePosition || imageUrl)
        doc.template.image = {}
      if (imagePosition)
        doc.template.image.position = imagePosition
      if (imageUrl)
        doc.template.image.url = imageUrl
      let response
      try {
        setLoadingDisplay(true)
        response = await api.update_display(project._id, displayId, doc)
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to update display' }))
      } finally {
        setLoadingDisplay(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Saved display',
        color: 'success',
        iconType: 'check'
      })
      setDisplay(doc)
    })()
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
        setLoadingDocRandom(true)
        response = await api.search(display.index_pattern, body)
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to get doc' }))
      } finally {
        setLoadingDocRandom(false)
      }

      // Handle API response
      setDoc(response.data.hits.hits[0])
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
        setLoadingDocRandom(true)
        response = await api.search(display.index_pattern, body)
      } catch (err) {
        return addToast(api.errorToast(error, { title: 'Failed to get doc' }))
      } finally {
        setLoadingDocRandom(false)
      }

      // Handle API response
      setDoc(response.data.hits.hits[0])
    })()
  }


  ////  Render  ////////////////////////////////////////////////////////////////

  const renderEditor = () => {
    return (
      <Editor
        defaultLanguage='markdown'
        height='100%'
        onChange={(value, event) => setBodyDraft(value)}
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
        value={bodyDraft}
      />
    )
  }

  /**
   * Check if the draft template differs from the saved template.
   */
  const doesDraftDiffer = () => {
    if (display.template?.image?.position != imagePosition)
      return true
    if (display.template?.image?.url != imageUrl)
      return true
    if (display.template?.body != bodyDraft)
      return true
    return false
  }

  return (<>
    <Page title={
      <EuiSkeletonTitle isLoading={loadingDisplay} size='l'>
        {!display.index_pattern &&
          <>Not found</>
        }
        {!!display.index_pattern &&
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
                    disabled={loadingDisplay || !doesDraftDiffer()}
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
                    disabled={loadingDisplay || !doesDraftDiffer()}
                    onClick={() => { setBodyDraft(display.template.body) }}
                  >
                    Reset
                  </EuiButton>
                </EuiFlexItem>
              </EuiFlexGroup>
              <EuiSpacer size='m' />

              {/* Editor */}
              <EuiFormRow fullWidth label='Markdown editor'>
                <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none'>
                  <EuiSkeletonText lines={21} isLoading={loadingProject || loadingIndices}>
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
                    onChange={(e) => setImageUrl(e.target.value)}
                    placeholder='http://my-image-server/{{ image.path }}'
                    prepend='Image URL'
                    value={imageUrl}
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
                      fill={imagePosition == 'top-left' ? true : false}
                      onClick={() => setImagePosition('top-left')}
                      size='s'
                      style={{ minWidth: '16px', padding: '8px', /*borderLeft: '0', borderRadius: '0'*/ borderBottomRightRadius: '0', borderTopRightRadius: '0' }}
                    >
                      <IconBoxAlignTopLeftFilled stroke={1.5} size={16} />
                    </EuiButton>
                  </EuiToolTip>
                  <EuiToolTip content='Align top right'>
                    <EuiButton
                      color='text'
                      fill={imagePosition == 'top-right' ? true : false}
                      onClick={() => setImagePosition('top-right')}
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
                disabled={!indices || loadingDocRandom}
                iconType='refresh'
                isLoading={loadingDocRandom}
                onClick={onGetDocRandom}
              >
                Random doc
              </EuiButton>
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiFieldSearch
                disabled={!indices || loadingDocById}
                fullWidth
                isLoading={loadingDocById}
                placeholder='...or doc _id'
                value={queryString}
                onChange={(e) => setQueryString(e.target.value)}
                onSearch={onGetDocById}
              />
            </EuiFlexItem>
          </EuiFlexGroup>
          <EuiSpacer size='l' />

          {/* Body */}
          <EuiSkeletonText lines={10} isLoading={loadingDocById || loadingDocRandom}>
            {doc &&
              <EuiFormRow fullWidth label='Example (large)'>
                <EuiFlexGroup>
                  <EuiFlexItem grow={10}>
                    <DocCard doc={doc} body={bodyDraft} imagePosition={imagePosition} imageUrl={imageUrl} />
                  </EuiFlexItem>
                </EuiFlexGroup>
              </EuiFormRow>
            }
          </EuiSkeletonText>
          <EuiSpacer size='m' />
          <EuiSkeletonText lines={10} isLoading={loadingDocById || loadingDocRandom}>
            {doc &&
              <EuiFormRow fullWidth label='Example (small)'>
                <EuiFlexGroup>
                  <EuiFlexItem grow={5}>
                    <DocCard doc={doc} body={bodyDraft} imagePosition={imagePosition} imageUrl={imageUrl} />
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