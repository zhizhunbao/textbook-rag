'use client'

import { createContext, useContext, useState, type ReactNode } from 'react'
import { useChatHistory } from './useChatHistory'

type ChatHistoryAPI = ReturnType<typeof useChatHistory>

interface ContextValue extends ChatHistoryAPI {
  activeSessionId: string | null
  setActiveSessionId: (id: string | null) => void
}

const ChatHistoryContext = createContext<ContextValue | null>(null)

export function ChatHistoryProvider({ children }: { children: ReactNode }) {
  const api = useChatHistory()
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)

  return (
    <ChatHistoryContext.Provider value={{ ...api, activeSessionId, setActiveSessionId }}>
      {children}
    </ChatHistoryContext.Provider>
  )
}

export function useChatHistoryContext() {
  const ctx = useContext(ChatHistoryContext)
  if (!ctx) throw new Error('useChatHistoryContext: missing ChatHistoryProvider')
  return ctx
}
