/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { createContext, useContext, useEffect, useState, useMemo } from 'react'
import api from '../api'
import utils from '../utils'
import { useAppContext } from './AppContext'

export const ChatContext = createContext()

export const useChatContext = () => useContext(ChatContext)

export const ChatProvider = ({ children }) => {
  const { addToast } = useAppContext()
  
  ////  State  /////////////////////////////////////////////////////////////////

  const [chatOpen, setChatOpen] = useState(() => {
    const val = localStorage.getItem('chatOpen')
    return val === null ? true : val === 'true' // defaults to true
  })
  const [conversation, setConversation] = useState([])
  const [conversationId, setConversationId] = useState(() => {
    return localStorage.getItem('conversationId') || null
  })
  const [conversationTitle, setConversationTitle] = useState(() => {
    return localStorage.getItem('conversationTitle') || 'New conversation'
  })
  const [currentMessage, setCurrentMessage] = useState('')
  const [inferenceId, setInferenceId] = useState(() => {
    return localStorage.getItem('inferenceId') || '.rainbow-sprinkles-elastic'
  })
  const [isConversationLoading, setIsConversationLoading] = useState(false)

  ////  Effects  ///////////////////////////////////////////////////////////////

  useEffect(() => localStorage.setItem('chatOpen', chatOpen), [chatOpen])
  useEffect(() => {
    if (conversationId) localStorage.setItem('conversationId', conversationId)
    else localStorage.removeItem('conversationId')
  }, [conversationId])
  useEffect(() => localStorage.setItem('conversationTitle', conversationTitle), [conversationTitle])
  useEffect(() => localStorage.setItem('inferenceId', inferenceId), [inferenceId])

  useEffect(() => {
    let active = true
    const loadConversation = async () => {
      if (conversationId && conversation.length === 0) {
        setIsConversationLoading(true)
        try {
          const response = await api.conversations_get(conversationId)
          if (!active) return

          // Handle 404 explicitly
          if (response.status === 404) {
            console.warn('Conversation not found:', conversationId)
            addToast({
              title: 'Conversation not found',
              text: 'This conversation may have been deleted.',
              color: 'danger',
              iconType: 'alert'
            })
            setConversationId(null)
            setConversationTitle('New conversation')
            return
          }

          const docs = utils.hitsToDocs(response)
          if (docs.length > 0) {
            const doc = docs[0]
            setConversation(doc.rounds || [])
            setConversationTitle(doc.title || 'Conversation')
          }
        } catch (e) {
          if (!active) return
          console.error('Failed to load conversation:', e)
        } finally {
          if (active) setIsConversationLoading(false)
        }
      }
    }
    loadConversation()
    return () => { active = false }
  }, [conversationId])

  const value = useMemo(() => ({
    chatOpen,
    conversation,
    conversationId,
    conversationTitle,
    currentMessage,
    inferenceId,
    isConversationLoading,
    setChatOpen,
    setConversation,
    setConversationId,
    setConversationTitle,
    setCurrentMessage,
    setInferenceId,
    setIsConversationLoading,
  }), [chatOpen, conversation, conversationId, conversationTitle, currentMessage, inferenceId, isConversationLoading])

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  )
}
