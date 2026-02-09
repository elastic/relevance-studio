/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useRef, useState } from 'react'
import { matchPath, useLocation } from 'react-router-dom'
import {
  EuiAccordion,
  EuiButton,
  EuiButtonEmpty,
  EuiButtonIcon,
  EuiCodeBlock,
  EuiConfirmModal,
  EuiContextMenuItem,
  EuiContextMenuPanel,
  EuiFieldSearch,
  EuiFieldText,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFlyout,
  EuiFlyoutBody,
  EuiFlyoutFooter,
  EuiFlyoutHeader,
  EuiHorizontalRule,
  EuiIcon,
  EuiLink,
  EuiLoadingElastic,
  EuiLoadingSpinner,
  EuiMarkdownFormat,
  EuiModal,
  EuiModalBody,
  EuiModalHeader,
  EuiModalHeaderTitle,
  EuiPanel,
  EuiPopover,
  EuiPortal,
  EuiSpacer,
  EuiSplitPanel,
  EuiText,
  EuiTextArea,
  EuiTitle,
  EuiToolTip,
} from '@elastic/eui'

// Custom User Message component with truncation/expansion
const UserMessageBubble = ({ content }) => {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
  const truncationLimit = 250 // Character limit before truncation
  const shouldTruncate = content.length > truncationLimit

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}
    >
      <EuiPanel
        color="primary"
        hasShadow={false}
        hasBorder={false}
        paddingSize="m"
        style={{
          borderRadius: '12px',
          borderBottomRightRadius: '2px',
          position: 'relative',
          maxWidth: '100%',
        }}
      >
        <EuiFlexGroup gutterSize="s" responsive={false} alignItems="flexStart">
          <EuiFlexItem>
            <EuiText
              size="m"
              style={
                !isExpanded && shouldTruncate
                  ? {
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    wordBreak: 'break-word',
                  }
                  : { wordBreak: 'break-word' }
              }
            >
              {content}
            </EuiText>
          </EuiFlexItem>
          {shouldTruncate && (
            <EuiFlexItem grow={false}>
              <EuiToolTip content={isExpanded ? 'Collapse text' : 'Expand text'}>
                <EuiButtonIcon
                  display="base"
                  size="s"
                  iconType={isExpanded ? 'arrowUp' : 'arrowDown'}
                  onClick={() => setIsExpanded(!isExpanded)}
                  aria-label={isExpanded ? 'Collapse text' : 'Expand text'}
                  color="ghost"
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    borderRadius: '50%',
                  }}
                />
              </EuiToolTip>
            </EuiFlexItem>
          )}
        </EuiFlexGroup>
      </EuiPanel>
      <div
        style={{
          marginTop: '8px',
          opacity: isHovered ? 1 : 0,
          transition: 'opacity 150ms ease-in-out',
        }}
      >
        <EuiButtonIcon
          aria-label="Copy message"
          color="text"
          display="empty"
          iconType="copy"
          size="xs"
          onClick={() => {
            navigator.clipboard.writeText(content)
          }}
        />
      </div>
    </div>
  )
}

// Reasoning Panel Component
const ReasoningPanel = ({ round, isSending }) => {
  const { steps = [], model_usage, time_to_last_token } = round || {}
  const [isExpanded, setIsExpanded] = useState(false)
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [expandedToolCallId, setExpandedToolCallId] = useState(null)

  const hasContent = (steps && steps.length > 0) || model_usage || time_to_last_token;
  if (!isSending && !hasContent) return null

  const toggleExpand = () => setIsExpanded(!isExpanded)

  const getStatusText = () => {
    if (round.status === 'completed' || time_to_last_token || (!isSending && round.status !== 'failed'))
      return 'Completed reasoning';
    if (round.status === 'failed')
      return 'Failed';
    if (round.status === 'pending')
      return 'Pending...';

    const latestStep = steps && steps.length > 0 ? steps[steps.length - 1] : null;
    if (!latestStep)
      return 'Thinking...';
    if (latestStep.type === 'reasoning')
      return latestStep.reasoning || 'Reasoning...';
    if (latestStep.type === 'tool_call')
      return `Calling tool ${latestStep.tool_id}...`;
    return 'Thinking...';
  };

  return (
    <div style={{ marginBottom: '16px' }}>
      {!isExpanded ? (
        <EuiFlexGroup gutterSize="s" alignItems="center" responsive={false} style={{ cursor: 'pointer', maxWidth: '100%' }} onClick={toggleExpand}>
          <EuiFlexItem grow={false}>
            {round.status === 'failed' ? (
              <EuiIcon type="error" size="m" color="danger" />
            ) : round.status === 'pending' ? (
              <EuiIcon type="clock" size="m" color="subdued" />
            ) : (round.status === 'completed' || getStatusText() === 'Completed reasoning') ? (
              <EuiIcon type="sparkles" size="m" color="text" />
            ) : (
              <EuiLoadingElastic size="m" />
            )}
          </EuiFlexItem>
          <EuiFlexItem grow={false} style={{ minWidth: 0 }}>
            <EuiText size="s" color="subdued" className="eui-textTruncate">
              {getStatusText()}
            </EuiText>
          </EuiFlexItem>
          <EuiFlexItem grow={false}>
            <EuiIcon type="arrowRight" size="s" color="subdued" />
          </EuiFlexItem>
        </EuiFlexGroup>
      ) : (
        <EuiPanel paddingSize="m" style={{ borderRadius: '16px', marginBottom: '24px' }}>
          <EuiFlexGroup justifyContent="spaceBetween" alignItems="center" responsive={false} style={{ marginBottom: '12px', cursor: 'pointer' }} onClick={toggleExpand}>
            <EuiFlexItem grow={false}>
              <EuiFlexGroup gutterSize="s" alignItems="center" responsive={false}>
                <EuiFlexItem grow={false}>
                  {round.status === 'failed' ? (
                    <EuiIcon type="error" size="m" color="danger" />
                  ) : round.status === 'pending' ? (
                    <EuiIcon type="clock" size="m" color="subdued" />
                  ) : (round.status === 'completed' || getStatusText() === 'Completed reasoning') ? (
                    <EuiIcon type="sparkles" size="m" color="text" />
                  ) : (
                    <EuiLoadingElastic size="m" />
                  )}
                </EuiFlexItem>
                <EuiFlexItem grow={false}><EuiText size="m"><strong>Reasoning</strong></EuiText></EuiFlexItem>
              </EuiFlexGroup>
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiIcon type="arrowDown" size="s" color="subdued" />
            </EuiFlexItem>
          </EuiFlexGroup>

          <EuiFlexGroup direction="column" gutterSize="s">
            {(steps || []).map((step, idx) => {
              const hasParams = step.params && (typeof step.params === 'string' ? step.params.replace(/\s/g, '') !== '{}' : Object.keys(step.params).length > 0)

              return (
                <EuiFlexItem key={idx}>
                  <EuiFlexGroup gutterSize="s" alignItems="flexStart" responsive={false}>
                    <EuiFlexItem grow={false} style={{ marginTop: '2px' }}>
                      {step.results?.some(r => r.type === 'error') ? (
                        <EuiIcon type="error" color="danger" size="m" />
                      ) : (step.results?.length > 0 || (step.type === 'reasoning' && step.reasoning)) ? (
                        <EuiIcon type="check" color="success" size="m" />
                      ) : (
                        <EuiLoadingSpinner size="s" />
                      )}
                    </EuiFlexItem>
                    <EuiFlexItem>
                      {step.type === 'reasoning' ? (
                        <EuiText size="s" color="subdued">{step.reasoning}</EuiText>
                      ) : (
                        <EuiAccordion
                          id={`step-${step.tool_call_id}`}
                          arrowDisplay={hasParams ? 'right' : 'none'}
                          buttonContent={
                            <EuiFlexGroup gutterSize="xs" alignItems="center" responsive={false}>
                              <EuiFlexItem grow={false}>
                                <EuiText size="s" color="subdued">Calling tool </EuiText>
                              </EuiFlexItem>
                              <EuiFlexItem grow={false}>
                                <EuiLink size="s" color="subdued">
                                  {step.tool_id}
                                </EuiLink>
                              </EuiFlexItem>
                              <EuiFlexItem grow={false}>
                                <EuiIcon type="popout" size="s" color="subdued" />
                              </EuiFlexItem>
                            </EuiFlexGroup>
                          }
                          paddingSize="none"
                        >
                          <div style={{ marginTop: '8px', marginLeft: '4px', paddingBottom: '8px' }}>
                            {hasParams && (
                              <EuiSplitPanel.Outer direction="column" hasBorder={true} style={{ marginBottom: '8px' }}>
                                <EuiSplitPanel.Inner paddingSize="m" color="plain">
                                  <EuiText size="s"><strong>Parameters</strong></EuiText>
                                </EuiSplitPanel.Inner>
                                <EuiSplitPanel.Inner paddingSize="none" color="transparent">
                                  <EuiCodeBlock language="json" fontSize="s" paddingSize="m" isCopyable>
                                    {(() => {
                                      try {
                                        const parsed = typeof step.params === 'string' ? JSON.parse(step.params) : step.params
                                        return JSON.stringify(parsed, null, 2)
                                      } catch (e) {
                                        return String(step.params)
                                      }
                                    })()}
                                  </EuiCodeBlock>
                                </EuiSplitPanel.Inner>
                              </EuiSplitPanel.Outer>
                            )}
                          </div>
                        </EuiAccordion>
                      )}
                    </EuiFlexItem>
                  </EuiFlexGroup>
                </EuiFlexItem>
              )
            })}
          </EuiFlexGroup>

          {(model_usage || round.time_to_last_token) && (
            <>
              <EuiSpacer size="m" />
              <div style={{ borderTop: '1px solid rgba(0,0,0,0.05)', paddingTop: '12px' }}>
                <EuiFlexGroup justifyContent="spaceBetween" alignItems="center">
                  <EuiFlexItem grow={false}>
                    <EuiFlexGroup gutterSize="m" alignItems="center" responsive={false}>
                      {round.time_to_last_token && (
                        <EuiFlexItem grow={false}>
                          <EuiFlexGroup gutterSize="xs" alignItems="center" responsive={false}>
                            <EuiIcon type="clock" size="m" color="subdued" />
                            <EuiText size="xs" color="subdued">{(round.time_to_last_token / 1000).toFixed(1)}s</EuiText>
                          </EuiFlexGroup>
                        </EuiFlexItem>
                      )}
                      {model_usage && (
                        <>
                          <EuiFlexItem grow={false}>
                            <EuiFlexGroup gutterSize="xs" alignItems="center" responsive={false}>
                              <EuiIcon type="sortUp" size="m" color="subdued" />
                              <EuiText size="xs" color="subdued">{model_usage.input_tokens?.toLocaleString()} tokens</EuiText>
                            </EuiFlexGroup>
                          </EuiFlexItem>
                          <EuiFlexItem grow={false}>
                            <EuiFlexGroup gutterSize="xs" alignItems="center" responsive={false}>
                              <EuiIcon type="sortDown" size="m" color="subdued" />
                              <EuiText size="xs" color="subdued">{model_usage.output_tokens?.toLocaleString()} tokens</EuiText>
                            </EuiFlexGroup>
                          </EuiFlexItem>
                        </>
                      )}
                    </EuiFlexGroup>
                  </EuiFlexItem>
                  <EuiFlexItem grow={false}>
                    <EuiButton color="text" display="base" size="s" iconType="code" onClick={() => setIsModalVisible(true)}>
                      <EuiText size="xs">
                        View JSON
                      </EuiText>
                    </EuiButton>
                  </EuiFlexItem>
                </EuiFlexGroup>
              </div>
            </>
          )}
        </EuiPanel>
      )}

      {isModalVisible && (
        <EuiModal onClose={() => setIsModalVisible(false)} style={{ width: '800px' }}>
          <EuiModalHeader><EuiModalHeaderTitle>Reasoning JSON</EuiModalHeaderTitle></EuiModalHeader>
          <EuiModalBody>
            <EuiCodeBlock language="json" fontSize="s" paddingSize="s" overflowHeight={600} isCopyable>
              {JSON.stringify(round, null, 2)}
            </EuiCodeBlock>
          </EuiModalBody>
        </EuiModal>
      )}
    </div>
  )
}

// Round Component
const RoundItem = ({ round, latestUserMessageRef, isSending }) => {
  return (
    <EuiFlexItem grow={false} ref={latestUserMessageRef}>
      {/* User Input */}
      <EuiFlexGroup justifyContent="flexEnd" responsive={false}>
        <EuiFlexItem grow={false} style={{ maxWidth: '80%', paddingRight: '8px' }}>
          <UserMessageBubble content={round.input.message} />
        </EuiFlexItem>
      </EuiFlexGroup>

      <EuiSpacer size="m" />

      {/* Agent Response */}
      <EuiFlexGroup justifyContent="flexStart" responsive={false}>
        <EuiFlexItem grow={false} style={{ width: '100%' }}>
          <EuiPanel color="transparent" hasBorder={false} hasShadow={false} paddingSize="s">
            {/* Reasoning and Tool Calls */}
            <ReasoningPanel round={round} isSending={isSending} />

            {/* Final Response Message */}
            {round.response?.message && (
              <>
                <EuiMarkdownFormat>
                  {round.response.message}
                </EuiMarkdownFormat>
                <div style={{ marginTop: '8px' }}>
                  <EuiButtonIcon
                    aria-label="Copy message"
                    color='text'
                    display="empty"
                    iconType="copy"
                    size="xs"
                    onClick={() => {
                      navigator.clipboard.writeText(round.response.message)
                    }}
                  />
                </div>
              </>
            )}
          </EuiPanel>
        </EuiFlexItem>
      </EuiFlexGroup>
    </EuiFlexItem>
  )
}

import api from '../api'
import utils from '../utils'
import { useAppContext } from '../Contexts/AppContext'
import { useChatContext } from '../Contexts/ChatContext'

// Custom useDebounce hook
const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)
    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

const Chat = () => {
  const { addToast, darkMode, hasCheckedSetup, licenseStatus, licenseType } = useAppContext()
  const {
    inferenceId,
    setInferenceId,
    conversation,
    setConversation,
    conversationId,
    setConversationId,
    conversationTitle,
    setConversationTitle,
    currentMessage,
    setCurrentMessage,
    isConversationLoading,
    chatOpen,
    setChatOpen,
  } = useChatContext()
  const isFlyoutOpen = chatOpen
  const closeFlyout = () => setChatOpen(false)
  const location = useLocation()
  const match = matchPath(location.pathname, {
    path: [
      '/workspaces/:workspace_id/benchmarks/:benchmark_id/evaluations/:evaluation_id',
      '/workspaces/:workspace_id/benchmarks/:benchmark_id',
      '/workspaces/:workspace_id/strategies/:strategy_id',
      '/workspaces/:workspace_id/displays/:display_id',
      '/workspaces/:workspace_id',
    ],
    exact: false,
    strict: false
  })
  const params = match?.params || {}
  const [isSending, setIsSending] = useState(false)
  const [isFocused, setIsFocused] = useState(false)
  const [availableEndpoints, setAvailableEndpoints] = useState(null)
  const [isPopoverOpen, setIsPopoverOpen] = useState(false)
  const [isHistoryPopoverOpen, setIsHistoryPopoverOpen] = useState(false)
  const [historySearchText, setHistorySearchText] = useState('')
  const [conversations, setConversations] = useState([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [isEditingTitle, setIsEditingTitle] = useState(false)
  const [isTitleHovered, setIsTitleHovered] = useState(false)
  const [tempTitle, setTempTitle] = useState('')
  const [hoveredConvId, setHoveredConvId] = useState(null)
  const [conversationToDelete, setConversationToDelete] = useState(null)
  const latestUserMessageRef = useRef(null)
  const textAreaRef = useRef(null)
  const historySearchRef = useRef(null)
  const abortControllerRef = useRef(null)
  const conversationRef = useRef(conversation)
  const lastProcessedInferenceConvId = useRef(null)
  const debouncedIsSending = useDebounce(isSending, 500)

  useEffect(() => {
    conversationRef.current = conversation
  }, [conversation])

  useEffect(() => {
    const fetchEndpoints = async () => {
      try {
        const response = await api.chat_endpoints()
        setAvailableEndpoints(response.data || [])
      } catch (error) {
        console.error("Error fetching inference endpoints:", error)
        setAvailableEndpoints([])
      }
    }
    fetchEndpoints()
  }, [])

  // Validate and update inferenceId based on available endpoints
  useEffect(() => {
    if (availableEndpoints === null)
      return
    const validIds = availableEndpoints.map(e => e.inference_id)
    const isCurrentIdValid = inferenceId && validIds.includes(inferenceId)
    if (!isCurrentIdValid) {
      if (validIds.includes('.rainbow-sprinkles-elastic')) {
        setInferenceId('.rainbow-sprinkles-elastic')
      } else if (availableEndpoints.length > 0) {
        setInferenceId(availableEndpoints[0].inference_id)
      } else {
        if (inferenceId !== '') setInferenceId('')
      }
    }
  }, [availableEndpoints, inferenceId, setInferenceId])

  // Restore inferenceId from conversation history when loaded
  useEffect(() => {
    if (!conversationId || conversation.length === 0 || availableEndpoints === null) {
      if (!conversationId) lastProcessedInferenceConvId.current = null
      return
    }

    if (lastProcessedInferenceConvId.current === conversationId) return

    const lastRoundWithInferenceId = [...conversation].reverse().find(r => r.model_usage?.inference_id)
    if (lastRoundWithInferenceId) {
      const lastId = lastRoundWithInferenceId.model_usage.inference_id
      const isValid = availableEndpoints.some(e => e.inference_id === lastId)
      if (isValid) {
        setInferenceId(lastId)
      }
    }
    lastProcessedInferenceConvId.current = conversationId
  }, [conversationId, conversation, availableEndpoints, setInferenceId])

  useEffect(() => {
    if (isHistoryPopoverOpen) {
      fetchConversations()
      setTimeout(() => {
        historySearchRef.current?.focus()
      }, 0)
    }
  }, [isHistoryPopoverOpen, historySearchText])

  const fetchConversations = async () => {
    setIsLoadingHistory(true)
    try {
      const response = await api.conversations_search({
        text: `title:*${historySearchText}*`,
        size: 10,
        sort: { field: '@meta.created_at', order: 'desc' }
      })
      setConversations(utils.hitsToDocs(response))
    } catch (error) {
      console.error("Error fetching conversations:", error)
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const handleSelectConversation = async (conv) => {
    setConversationId(conv.id || conv._id)
    setConversationTitle(conv.title)
    setConversation(conv.rounds || [])
    setIsHistoryPopoverOpen(false)
  }

  const handleNewConversation = () => {
    setConversationId(null)
    setConversationTitle('New conversation')
    setConversation([])
    setCurrentMessage('')
    setIsHistoryPopoverOpen(false)
    setTimeout(() => {
      textAreaRef.current?.focus()
    }, 0)
  }

  const handleDeleteConversation = (e, conv) => {
    e.stopPropagation()
    setConversationToDelete(conv)
  }

  const confirmDeleteConversation = async () => {
    if (!conversationToDelete) return
    const convId = conversationToDelete.id || conversationToDelete._id
    try {
      await api.conversations_delete(convId)
      setConversations((prev) => prev.filter((c) => (c.id || c._id) !== convId))
      if (conversationId === convId) {
        handleNewConversation()
      }
    } catch (error) {
      console.error("Error deleting conversation:", error)
    } finally {
      setConversationToDelete(null)
    }
  }

  const handleStartRename = () => {
    setTempTitle(conversationTitle)
    setIsEditingTitle(true)
  }

  const handleSaveRename = async () => {
    if (!tempTitle.trim() || tempTitle === conversationTitle) {
      setIsEditingTitle(false)
      return
    }

    try {
      if (conversationId) {
        await api.conversations_update(conversationId, { title: tempTitle })
        setConversationTitle(tempTitle)
      } else {
        setConversationTitle(tempTitle)
      }
      setIsEditingTitle(false)
    } catch (error) {
      console.error("Error renaming conversation:", error)
    }
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!currentMessage.trim() || isSending) return

    const ui_context = {
      ...params,
      route: location.pathname,
    }

    const convId = conversationId || crypto.randomUUID()
    const isNew = !conversationId
    const roundId = crypto.randomUUID()

    const newRound = {
      id: roundId,
      status: 'pending',
      input: { message: currentMessage },
      response: { message: '' },
      steps: []
    }

    const updatedRounds = [...conversation, newRound]
    setConversation(updatedRounds)
    setCurrentMessage('')
    setIsSending(true)

    // If this is a new conversation, create it immediately so it appears in history and has a title
    if (isNew) {
      const title = currentMessage.substring(0, 50) + (currentMessage.length > 50 ? '...' : '')
      setConversationId(convId)
      setConversationTitle(title)
      api.conversations_create({
        id: convId,
        conversation_id: convId,
        title,
        rounds: updatedRounds
      }).catch(err => console.error("Error creating initial conversation:", err))
    } else {
      // For existing conversations, update immediately and check for existence
      try {
        const response = await api.conversations_update(convId, {
          rounds: updatedRounds
        })
        if (response.status === 404) {
          addToast({
            title: 'Conversation not found',
            text: 'This conversation may have been deleted.',
            color: 'danger',
            iconType: 'alert'
          })
          setIsSending(false)
          return
        }
      } catch (err) {
        console.error("Error updating conversation before chat:", err)
      }
    }

    // Scroll to the latest user message
    setTimeout(() => {
      latestUserMessageRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 0)

    abortControllerRef.current = new AbortController()
    const signal = abortControllerRef.current.signal

    const startTime = Date.now()

    try {
      let lineBuffer = ''
      let needsNewline = false
      const onChunk = (chunk) => {
        lineBuffer += chunk.data
        const lines = lineBuffer.split('\n')
        lineBuffer = lines.pop()

        lines.forEach(line => {
          line = line.trim()
          if (!line || line.startsWith('event:') || line.startsWith(':')) return
          if (line.startsWith('data:')) {
            const data = line.substring(5).trim()
            if (data === '[DONE]') return

            try {
              const eventData = JSON.parse(data)
              const { event, data: payload } = eventData

              setConversation((prev) => {
                const newRounds = [...prev]
                const currentRound = newRounds[newRounds.length - 1]

                switch (event) {
                  case 'conversation_id_set':
                    if (!conversationId) setConversationId(payload.conversation_id)
                    break
                  case 'reasoning':
                    // Append to last step if it's reasoning, otherwise create new reasoning step
                    {
                      let lastStep = currentRound.steps[currentRound.steps.length - 1]
                      if (lastStep && lastStep.type === 'reasoning') {
                        lastStep.reasoning += payload.reasoning
                      } else {
                        currentRound.steps.push({ type: 'reasoning', reasoning: payload.reasoning })
                      }
                    }
                    break
                  case 'tool_call':
                    // If a tool call starts, we just push it
                    currentRound.steps.push({
                      type: 'tool_call',
                      tool_id: payload.tool_id,
                      tool_call_id: payload.tool_call_id,
                      params: payload.params,
                      results: []
                    })
                    break
                  case 'tool_result':
                    {
                      const toolStep = currentRound.steps.find(s => s.tool_call_id === payload.tool_call_id)
                      if (toolStep) {
                        toolStep.results.push({
                          type: payload.type || 'success',
                          data: payload.data
                        })
                      }
                    }
                    break
                  case 'model_usage':
                    currentRound.model_usage = payload
                    needsNewline = true
                    break
                  case 'round_info':
                    Object.assign(currentRound, payload)
                    break
                  case 'round':
                    if (needsNewline && currentRound.response.message.length > 0) {
                      currentRound.response.message += '\n\n'
                    }
                    currentRound.response.message += payload.message || ''
                    needsNewline = false
                    break
                  default:
                    // Handle old format for backward compatibility or unexpected formats
                    if (eventData.choices?.[0]?.delta?.content) {
                      if (needsNewline && currentRound.response.message.length > 0) {
                        currentRound.response.message += '\n\n'
                      }
                      currentRound.response.message += eventData.choices[0].delta.content
                      needsNewline = false
                    }
                }
                return newRounds
              })
            } catch (error) {
              console.error("Error parsing streaming JSON:", error, ":", data)
            }
          }
        })
      }

      await api.chat(updatedRounds, inferenceId, onChunk, signal, ui_context, convId, convId)

    } catch (error) {
      if (error.name === 'AbortError') {
        console.log("Chat aborted")
      } else {
        console.error("Error in chat:", error)
      }
    } finally {
      setIsSending(false)
      abortControllerRef.current = null

      setTimeout(async () => {
        const finalRounds = [...conversationRef.current]

        try {
          const response = await api.conversations_update(convId, {
            rounds: finalRounds
          })

          if (response.status === 404) {
            if (!isNew) {
              addToast({
                title: 'Conversation not found',
                text: 'This conversation may have been deleted.',
                color: 'danger',
                iconType: 'alert'
              })
              handleNewConversation()
            } else {
              // Fallback to create if update fails for a new conversation (e.g. initial create failed)
              const title = newRound.input.message.substring(0, 50) + (newRound.input.message.length > 50 ? '...' : '')
              await api.conversations_create({
                id: convId,
                conversation_id: convId,
                title,
                rounds: finalRounds
              })
            }
          }
        } catch (saveError) {
          console.error("Error saving conversation:", saveError)
        }
      }, 100)
    }
  }

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      setIsSending(false)
    }
  }

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isFlyoutOpen) {
        closeFlyout()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isFlyoutOpen, closeFlyout])

  if (!isFlyoutOpen)
    return null

  if (!hasCheckedSetup)
    return null

  return (
    <EuiPortal>
      <EuiFlyout
        aria-labelledby="chatFlyoutTitle"
        className="chat"
        hideCloseButton={true}
        maxWidth="calc(100vw - 432px)"
        minWidth={432}
        ownFocus={false}
        resizable={true}
        side="right"
        size={600}
        style={{
          background: darkMode
            ? 'linear-gradient(rgb(11, 22, 40) 21.09%, rgb(7, 16, 31) 51.44%, rgb(11, 22, 40) 87.98%)'
            : 'linear-gradient(rgb(255, 255, 255) 21.09%, rgb(246, 249, 252) 51.44%, rgb(255, 255, 255) 87.98%)'
        }}
        type="push"
      >
        {(!hasCheckedSetup || availableEndpoints === null) ? (
          <>
            {/* Prerequisites of license and chat completion endpoints are still being checked */}
            <EuiFlyoutHeader hasBorder={false} style={{ padding: '16px' }}>
              <EuiFlexGroup justifyContent="spaceBetween" alignItems="center" responsive={false} style={{ height: '56px' }}>
                <EuiFlexItem grow={false} style={{ width: '80px' }} />
                <EuiFlexItem grow={false}>
                  <></>
                </EuiFlexItem>
                <EuiFlexItem grow={false} style={{ width: '80px', textAlign: 'right' }}>
                  <EuiFlexGroup gutterSize="s" alignItems="center" justifyContent="flexEnd" responsive={false}>
                    <EuiFlexItem grow={false}>
                      <EuiButtonIcon
                        color="text"
                        display="empty"
                        iconType="cross"
                        onClick={closeFlyout}
                        aria-label="Close"
                      />
                    </EuiFlexItem>
                  </EuiFlexGroup>
                </EuiFlexItem>
              </EuiFlexGroup>
            </EuiFlyoutHeader>
            <EuiFlyoutBody>
              <EuiFlexGroup alignItems="center" justifyContent="center" style={{ height: '100%' }}>
                <EuiLoadingSpinner size="xl" />
              </EuiFlexGroup>
            </EuiFlyoutBody>
            <EuiFlyoutFooter style={{ backgroundColor: 'transparent', padding: '16px' }}>
              <EuiFlexGroup justifyContent="center">
                <></>
              </EuiFlexGroup>
            </EuiFlyoutFooter>
          </>
        ) : (availableEndpoints?.length === 0 || licenseStatus !== 'active' || licenseType !== 'enterprise') ? (
          <>
            {/* At least one prerequisites of license or chat completion endpoints are not met. */}
            <EuiFlyoutHeader hasBorder={false} style={{ padding: '16px' }}>
              <EuiFlexGroup justifyContent="spaceBetween" alignItems="center" responsive={false} style={{ height: '56px' }}>
                <EuiFlexItem grow={false} style={{ width: '80px' }} />
                <EuiFlexItem grow={false} />
                <EuiFlexItem grow={false} style={{ width: '80px', textAlign: 'right' }}>
                  <EuiFlexGroup gutterSize="s" alignItems="center" justifyContent="flexEnd" responsive={false}>
                    <EuiFlexItem grow={false}>
                      <EuiButtonIcon
                        color="text"
                        display="empty"
                        iconType="cross"
                        onClick={closeFlyout}
                        aria-label="Close"
                      />
                    </EuiFlexItem>
                  </EuiFlexGroup>
                </EuiFlexItem>
              </EuiFlexGroup>
            </EuiFlyoutHeader>
            <EuiFlyoutBody>
              <EuiFlexGroup alignItems="center" justifyContent="center" style={{ padding: '32px' }}>
                <EuiPanel paddingSize="xl" style={{ textAlign: 'center' }}>
                  <EuiIcon color="subdued" type="plugs" size="l" />
                  <EuiSpacer size="l" />
                  <EuiTitle size="s">
                    <h3>Agent Not Ready</h3>
                  </EuiTitle>
                  <EuiSpacer size="l" />
                  {
                    licenseStatus === 'active' && licenseType === 'enterprise' &&
                    <>
                      <EuiText size="s">
                        <p>
                          Agents require a <span style={{ fontWeight: 500 }}>chat completion inference endpoint</span>.<br />
                          You can configure this in Kibana or Elasticsearch.
                        </p>
                      </EuiText>
                      <EuiSpacer size="l" />
                      <EuiButton
                        href="https://www.elastic.co/docs/explore-analyze/elastic-inference/inference-api"
                        iconSide="right"
                        iconSize="s"
                        iconType="popout"
                        size="s"
                        target="_blank"
                      >
                        Learn More
                      </EuiButton>
                    </>
                  }
                  {
                    (licenseStatus !== 'active' || licenseType !== 'enterprise') &&
                    <>
                      <EuiText size="s">
                        <p>
                          Agents require an active <a href="https://www.elastic.co/docs/deploy-manage/license" target="_blank">enterprise license</a><br />to use the <a href="https://www.elastic.co/docs/explore-analyze/elastic-inference/inference-api" target="_blank">Elasticsearch Inference API</a>.
                        </p>
                        <p>
                          Your license is: <span style={{ fontWeight: 500 }}>{licenseType || 'unknown'}</span> {!!licenseStatus && licenseStatus !== 'unknown' && <EuiText color="subdued" size="xs" component="span"><small>({licenseStatus})</small></EuiText>}
                        </p>
                      </EuiText>
                      <EuiSpacer size="l" />
                      <EuiButton
                        href="https://www.elastic.co/subscriptions"
                        iconSide="right"
                        iconSize="s"
                        iconType="popout"
                        size="s"
                        target="_blank"
                      >
                        Get a license
                      </EuiButton>
                    </>
                  }
                </EuiPanel>
              </EuiFlexGroup>
            </EuiFlyoutBody>
          </>
        ) : (
          <>
            {/* All prerequisites of license and chat completion endpoints are met. */}
            <EuiFlyoutHeader hasBorder={false} style={{ padding: '16px' }}>
              <EuiFlexGroup justifyContent="spaceBetween" alignItems="center" responsive={false} style={{ height: '56px' }}>
                {/* Left Section: History & New Chat */}
                <EuiFlexItem grow={false} style={{ width: '80px' }}>
                  <EuiFlexGroup gutterSize="s" alignItems="center" responsive={false}>
                    <EuiFlexItem grow={false}>
                      <EuiPopover
                        button={
                          conversationId || conversation.length > 0 ? (
                            <EuiButtonIcon
                              color="text"
                              display="empty"
                              iconType="clockCounter"
                              aria-label="Conversations"
                              onClick={() => setIsHistoryPopoverOpen(!isHistoryPopoverOpen)}
                            />
                          ) : (
                            <EuiButtonEmpty
                              color="text"
                              display="empty"
                              iconType="clockCounter"
                              onClick={() => setIsHistoryPopoverOpen(!isHistoryPopoverOpen)}
                              size="s"
                              style={{ fontWeight: 500 }}
                            >
                              Conversations
                            </EuiButtonEmpty>
                          )
                        }
                        isOpen={isHistoryPopoverOpen}
                        closePopover={() => setIsHistoryPopoverOpen(false)}
                        panelPaddingSize="none"
                        anchorPosition="downLeft"
                      >
                        <div style={{ width: '400px' }}>
                          <div style={{ padding: '8px' }}>
                            <EuiFieldSearch
                              placeholder="Search conversations"
                              fullWidth
                              compressed
                              value={historySearchText}
                              onChange={(e) => setHistorySearchText(e.target.value)}
                              inputRef={(el) => (historySearchRef.current = el)}
                            />
                          </div>
                          <EuiContextMenuPanel size="s">
                            {isLoadingHistory ? (
                              <EuiFlexGroup justifyContent="center" style={{ padding: '16px' }}>
                                <EuiLoadingSpinner size="m" />
                              </EuiFlexGroup>
                            ) : conversations.length > 0 ? (
                              <>
                                <EuiHorizontalRule margin="none" />
                                {conversations.map((conv) => (
                                  <div
                                    key={conv.id || conv._id}
                                    style={{ padding: '0 8px' }}
                                    onMouseEnter={() => setHoveredConvId(conv.id || conv._id)}
                                    onMouseLeave={() => setHoveredConvId(null)}
                                  >
                                    <EuiFlexGroup gutterSize="none" alignItems="center" responsive={false}>
                                      <EuiFlexItem>
                                        <EuiContextMenuItem
                                          size="s"
                                          onClick={() => handleSelectConversation(conv)}
                                          style={{ width: '100%' }}
                                        >
                                          {conv.title}
                                        </EuiContextMenuItem>
                                      </EuiFlexItem>
                                      <EuiFlexItem grow={false}>
                                        {hoveredConvId === (conv.id || conv._id) && (
                                          <EuiButtonIcon
                                            iconType="trash"
                                            color="danger"
                                            size="xs"
                                            aria-label="Delete conversation"
                                            onClick={(e) => handleDeleteConversation(e, conv)}
                                          />
                                        )}
                                      </EuiFlexItem>
                                    </EuiFlexGroup>
                                  </div>
                                ))}
                              </>
                            ) : (
                              <div style={{ padding: '16px', textAlign: 'center', color: 'gray' }}>
                                No conversations found
                              </div>
                            )}
                          </EuiContextMenuPanel>
                        </div>
                      </EuiPopover>
                    </EuiFlexItem>
                    {(conversationId || conversation.length > 0) && (
                      <EuiFlexItem grow={false}>
                        <EuiButtonIcon
                          color="text"
                          display="empty"
                          iconType="plus"
                          aria-label="New conversation"
                          onClick={handleNewConversation}
                        />
                      </EuiFlexItem>
                    )}
                  </EuiFlexGroup>
                </EuiFlexItem>

                {/* Center Section: Conversation Title */}
                <EuiFlexItem grow={true}>
                  {(conversation.length > 0 || conversationId) && (
                    <div
                      style={{ textAlign: 'center' }}
                      onMouseEnter={() => setIsTitleHovered(true)}
                      onMouseLeave={() => setIsTitleHovered(false)}
                    >
                      {isEditingTitle ? (
                        <EuiFlexGroup gutterSize="s" alignItems="center" justifyContent="center" responsive={false} style={{ height: '32px' }}>
                          <EuiFlexItem grow={true}>
                            <EuiFieldText
                              autoFocus
                              fullWidth
                              value={tempTitle}
                              onChange={(e) => setTempTitle(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleSaveRename()
                                if (e.key === 'Escape') setIsEditingTitle(false)
                              }}
                              onBlur={(e) => {
                                // Only save if we didn't click the cancel button
                                if (e.relatedTarget?.getAttribute('aria-label') === 'Cancel') return;
                                handleSaveRename();
                              }}
                              compressed
                            />
                          </EuiFlexItem>
                          <EuiFlexItem grow={false}>
                            <EuiFlexGroup gutterSize="xs" responsive={false}>
                              <EuiFlexItem grow={false}>
                                <EuiButtonIcon
                                  iconType="check"
                                  aria-label="Save"
                                  onClick={handleSaveRename}
                                  size="s"
                                  style={{
                                    backgroundColor: '#E1EBF9',
                                    color: '#005BB7',
                                    borderRadius: '4px',
                                    width: '32px',
                                    height: '32px'
                                  }}
                                />
                              </EuiFlexItem>
                              <EuiFlexItem grow={false}>
                                <EuiButtonIcon
                                  iconType="cross"
                                  aria-label="Cancel"
                                  onClick={() => setIsEditingTitle(false)}
                                  size="s"
                                  style={{
                                    backgroundColor: '#FEEBEC',
                                    color: '#BD271E',
                                    borderRadius: '4px',
                                    width: '32px',
                                    height: '32px'
                                  }}
                                />
                              </EuiFlexItem>
                            </EuiFlexGroup>
                          </EuiFlexItem>
                        </EuiFlexGroup>
                      ) : (
                        <EuiFlexGroup gutterSize="xs" alignItems="center" justifyContent="center" responsive={false} style={{ height: '32px' }}>
                          {/* Left Spacer to keep title centered */}
                          <EuiFlexItem grow={false} style={{ width: '32px' }} />

                          <EuiFlexItem grow={false} style={{ maxWidth: 'calc(100% - 64px)' }}>
                            <EuiTitle size="xs">
                              <h2
                                id="chatFlyoutTitle"
                                style={{
                                  fontWeight: 500,
                                  textAlign: 'center',
                                  lineHeight: '32px',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap'
                                }}
                              >
                                {conversationTitle}
                              </h2>
                            </EuiTitle>
                          </EuiFlexItem>

                          <EuiFlexItem grow={false} style={{ width: '32px' }}>
                            <EuiButtonIcon
                              iconType="pencil"
                              aria-label="Rename conversation"
                              onClick={handleStartRename}
                              size="s"
                              style={{
                                opacity: isTitleHovered ? 1 : 0,
                                pointerEvents: isTitleHovered ? 'auto' : 'none',
                                transition: 'opacity 150ms ease-in-out'
                              }}
                            />
                          </EuiFlexItem>
                        </EuiFlexGroup>
                      )}
                    </div>
                  )}
                </EuiFlexItem>

                {/* Right Section: More & Close */}
                <EuiFlexItem grow={false} style={{ width: '80px', textAlign: 'right' }}>
                  <EuiFlexGroup gutterSize="s" alignItems="center" justifyContent="flexEnd" responsive={false}>
                    <EuiFlexItem grow={false}>
                      <EuiButtonIcon
                        color="text"
                        display="empty"
                        iconType="cross"
                        onClick={closeFlyout}
                        aria-label="Close"
                      />
                    </EuiFlexItem>
                  </EuiFlexGroup>
                </EuiFlexItem>
              </EuiFlexGroup>
            </EuiFlyoutHeader>
            <EuiFlyoutBody style={{ padding: '0' }}>
              {isConversationLoading ? (
                <EuiFlexGroup alignItems="center" justifyContent="center" style={{ height: '100%' }}>
                  <EuiLoadingSpinner size="xl" />
                </EuiFlexGroup>
              ) : (
                <>
                  {conversation.length === 0 && !conversationId && (
                    <EuiFlexGroup alignItems="center" justifyContent="center" style={{ height: '100%' }}>
                      <EuiFlexItem grow>
                        <EuiTitle size="m">
                          <h2 style={{
                            bottom: '50%',
                            fontWeight: 400,
                            position: 'absolute',
                            textAlign: 'center',
                            top: '50%',
                            width: '100%',
                          }}>
                            How can I help you?
                          </h2>
                        </EuiTitle>
                      </EuiFlexItem>
                    </EuiFlexGroup>
                  )}
                  <EuiFlexGroup direction="column" gutterSize="l" responsive={false}>
                    {conversation.map((round, index) => (
                      <RoundItem
                        key={round.id || index}
                        round={round}
                        latestUserMessageRef={index === conversation.length - 1 ? latestUserMessageRef : null}
                        isSending={isSending && index === conversation.length - 1}
                      />
                    ))}
                  </EuiFlexGroup>
                </>
              )}
            </EuiFlyoutBody>
            <EuiFlyoutFooter style={{ backgroundColor: 'transparent', padding: '16px' }}>
              <form onSubmit={handleSendMessage}>
                <EuiPanel
                  color="plain"
                  paddingSize="m"
                  style={{
                    borderColor: isFocused ? 'rgb(11, 100, 221)' : 'rgba(0,0,0,0)',
                    borderRadius: '16px',
                    borderStyle: 'solid',
                    borderWidth: '1px',
                    boxShadow: isFocused ? '0 0 10px rgba(0, 0, 0, 0.25)' : undefined,
                    transition: 'all 250ms ease-in-out',
                  }}
                >
                  <EuiTextArea
                    disabled={isSending || isConversationLoading}
                    fullWidth
                    inputRef={(el) => { textAreaRef.current = el; }}
                    onBlur={() => setIsFocused(false)}
                    onChange={(e) => setCurrentMessage(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage(e);
                      }
                    }}
                    placeholder="Ask anything"
                    resize="none"
                    rows={2}
                    style={{
                      border: 'none',
                      boxShadow: 'none',
                      backgroundColor: 'transparent',
                      outline: 'none'
                    }}
                    value={currentMessage}
                  />
                  <EuiFlexGroup justifyContent="spaceBetween" alignItems="center" gutterSize="none" responsive={false}>
                    <EuiFlexItem grow={false} style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                      <EuiPopover
                        button={
                          <EuiButtonEmpty
                            color="text"
                            iconType="productML"
                            onClick={() => setIsPopoverOpen(!isPopoverOpen)}
                            size="s"
                            style={{ fontWeight: 500 }}
                          >
                            {inferenceId || 'Select model'}
                          </EuiButtonEmpty>
                        }
                        isOpen={isPopoverOpen}
                        closePopover={() => setIsPopoverOpen(false)}
                        panelPaddingSize="none"
                        anchorPosition="upLeft"
                      >
                        <EuiContextMenuPanel
                          size="s"
                          items={availableEndpoints.map(endpoint => (
                            <EuiContextMenuItem
                              icon={inferenceId === endpoint.inference_id ? 'check' : undefined}
                              key={endpoint.inference_id}
                              onClick={() => {
                                setInferenceId(endpoint.inference_id);
                                setIsPopoverOpen(false);
                              }}
                            >
                              {endpoint.inference_id}
                            </EuiContextMenuItem>
                          ))}
                        />
                      </EuiPopover>
                    </EuiFlexItem>
                    <EuiFlexItem grow={false}>
                      <EuiFlexGroup gutterSize="s" alignItems="center" responsive={false}>
                        <EuiFlexItem grow={false}>
                          <EuiButtonIcon
                            aria-label={isSending ? 'Cancel' : 'Send'}
                            color={isSending ? 'text' : 'primary'}
                            display={isSending ? 'base' : 'fill'}
                            iconType={isSending ? 'stopFill' : 'sortUp'}
                            isDisabled={isConversationLoading || (isSending ? false : !currentMessage.trim())}
                            onClick={isSending ? handleCancel : () => { }}
                            size="s"
                            style={{ borderRadius: '4px' }}
                            type={isSending ? "button" : "submit"}
                          />
                        </EuiFlexItem>
                      </EuiFlexGroup>
                    </EuiFlexItem>
                  </EuiFlexGroup>
                </EuiPanel>
              </form>
            </EuiFlyoutFooter>
          </>
        )}
      </EuiFlyout>

      {conversationToDelete && (
        <EuiConfirmModal
          title="Delete conversation"
          onCancel={() => setConversationToDelete(null)}
          onConfirm={confirmDeleteConversation}
          cancelButtonText="Cancel"
          confirmButtonText="Delete"
          buttonColor="danger"
          defaultFocusedButton="confirm"
        >
          <p>
            Are you sure you want to delete the conversation <strong>{conversationToDelete.title}</strong>? This action cannot be undone.
          </p>
        </EuiConfirmModal>
      )}
    </EuiPortal>
  )
}

export default Chat
