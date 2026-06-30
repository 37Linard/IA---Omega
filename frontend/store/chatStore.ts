'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Conversation, Message, AgentStep } from '@/lib/types'
import { generateId, extractTitle } from '@/lib/utils'

export interface HitlRequest {
  id: string
  action: string
  input: unknown
  message: string
}

export interface PendingTemplateTask {
  task: string
  templateId: string
  templateInputs: Record<string, string>
  displayLabel: string
}

interface ChatState {
  conversations: Conversation[]
  activeId: string | null
  theme: 'dark' | 'light'
  hitlRequest: HitlRequest | null
  pendingTemplateTask: PendingTemplateTask | null

  // Actions
  newConversation: () => string
  deleteConversation: (id: string) => void
  setActive: (id: string) => void
  addUserMessage: (content: string) => string
  startAssistantMessage: () => string
  appendToken: (msgId: string, token: string) => void
  appendFinalToken: (msgId: string, token: string) => void
  addStep: (msgId: string, step: Omit<AgentStep, 'id'>) => void
  appendThought: (msgId: string, token: string) => void
  finalizeMessage: (msgId: string, content?: string) => void
  resetContent: (msgId: string) => void
  setTokenUsage: (msgId: string, prompt: number, completion: number) => void
  setError: (msgId: string, error: string) => void
  setFeedback: (msgId: string, feedback: 'up' | 'down') => void
  setHitlRequest: (req: HitlRequest | null) => void
  setPendingTemplateTask: (task: PendingTemplateTask | null) => void
  toggleTheme: () => void
  getActive: () => Conversation | undefined
  renameConversation: (id: string, title: string) => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      activeId: null,
      theme: 'dark',
      hitlRequest: null,
      pendingTemplateTask: null,

      newConversation: () => {
        const id = generateId()
        const conv: Conversation = {
          id,
          title: 'Nova conversa',
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        }
        set(s => ({ conversations: [conv, ...s.conversations], activeId: id }))
        return id
      },

      deleteConversation: (id) => {
        set(s => {
          const convs = s.conversations.filter(c => c.id !== id)
          const activeId = s.activeId === id
            ? (convs[0]?.id ?? null)
            : s.activeId
          return { conversations: convs, activeId }
        })
      },

      renameConversation: (id, title) => {
        set(s => ({
          conversations: s.conversations.map(c =>
            c.id === id ? { ...c, title } : c
          )
        }))
      },

      setActive: (id) => set({ activeId: id }),

      addUserMessage: (content) => {
        const msgId = generateId()
        const msg: Message = {
          id: msgId,
          role: 'user',
          content,
          steps: [],
          isStreaming: false,
          streamingThought: '',
          timestamp: new Date(),
        }
        set(s => ({
          conversations: s.conversations.map(c =>
            c.id === s.activeId
              ? {
                  ...c,
                  messages: [...c.messages, msg],
                  title: c.messages.length === 0 ? extractTitle(content) : c.title,
                  updatedAt: new Date(),
                }
              : c
          ),
        }))
        return msgId
      },

      startAssistantMessage: () => {
        const msgId = generateId()
        const msg: Message = {
          id: msgId,
          role: 'assistant',
          content: '',
          steps: [],
          isStreaming: true,
          streamingThought: '',
          timestamp: new Date(),
        }
        set(s => ({
          conversations: s.conversations.map(c =>
            c.id === s.activeId
              ? { ...c, messages: [...c.messages, msg], updatedAt: new Date() }
              : c
          ),
        }))
        return msgId
      },

      appendToken: (msgId, token) => {
        set(s => ({
          conversations: s.conversations.map(c =>
            c.id === s.activeId
              ? {
                  ...c,
                  messages: c.messages.map(m =>
                    m.id === msgId
                      ? { ...m, streamingThought: m.streamingThought + token }
                      : m
                  ),
                }
              : c
          ),
        }))
      },

      appendFinalToken: (msgId, token) => {
        set(s => ({
          conversations: s.conversations.map(c =>
            c.id === s.activeId
              ? {
                  ...c,
                  messages: c.messages.map(m =>
                    m.id === msgId
                      ? { ...m, content: m.content + token, isStreaming: true }
                      : m
                  ),
                }
              : c
          ),
        }))
      },

      addStep: (msgId, step) => {
        const s = get()
        const fullStep: AgentStep = { id: generateId(), ...step }
        set(state => ({
          conversations: state.conversations.map(c =>
            c.id === s.activeId
              ? {
                  ...c,
                  messages: c.messages.map(m =>
                    m.id === msgId
                      ? { ...m, steps: [...m.steps, fullStep], streamingThought: '' }
                      : m
                  ),
                }
              : c
          ),
        }))
      },

      appendThought: (msgId, token) => {
        set(s => ({
          conversations: s.conversations.map(c =>
            c.id === s.activeId
              ? {
                  ...c,
                  messages: c.messages.map(m =>
                    m.id === msgId
                      ? { ...m, streamingThought: m.streamingThought + token }
                      : m
                  ),
                }
              : c
          ),
        }))
      },

      finalizeMessage: (msgId, content) => {
        set(s => ({
          conversations: s.conversations.map(c =>
            c.id === s.activeId
              ? {
                  ...c,
                  messages: c.messages.map(m =>
                    m.id === msgId
                      ? {
                          ...m,
                          content: content ?? m.content,
                          isStreaming: false,
                          streamingThought: '',
                        }
                      : m
                  ),
                }
              : c
          ),
        }))
      },

      resetContent: (msgId) => {
        set(s => ({
          conversations: s.conversations.map(c =>
            c.id === s.activeId
              ? {
                  ...c,
                  messages: c.messages.map(m =>
                    m.id === msgId ? { ...m, content: '', isStreaming: true } : m
                  ),
                }
              : c
          ),
        }))
      },

      setTokenUsage: (msgId, prompt, completion) => {
        set(s => ({
          conversations: s.conversations.map(c =>
            c.id === s.activeId
              ? {
                  ...c,
                  messages: c.messages.map(m =>
                    m.id === msgId
                      ? { ...m, tokenUsage: { prompt, completion } }
                      : m
                  ),
                }
              : c
          ),
        }))
      },

      setError: (msgId, error) => {
        set(s => ({
          conversations: s.conversations.map(c =>
            c.id === s.activeId
              ? {
                  ...c,
                  messages: c.messages.map(m =>
                    m.id === msgId
                      ? { ...m, error, isStreaming: false }
                      : m
                  ),
                }
              : c
          ),
        }))
      },

      setFeedback: (msgId, feedback) => {
        set(s => ({
          conversations: s.conversations.map(c => ({
            ...c,
            messages: c.messages.map(m =>
              m.id === msgId ? { ...m, feedback } : m
            ),
          })),
        }))
      },

      setHitlRequest: (req) => set({ hitlRequest: req }),

      setPendingTemplateTask: (task) => set({ pendingTemplateTask: task }),

      toggleTheme: () => set(s => ({ theme: s.theme === 'dark' ? 'light' : 'dark' })),

      getActive: () => {
        const s = get()
        return s.conversations.find(c => c.id === s.activeId)
      },
    }),
    {
      name: 'ia-chat-storage',
      partialize: (s) => ({
        conversations: s.conversations.map(c => ({
          ...c,
          messages: c.messages.slice(-100),
        })),
        activeId: s.activeId,
        theme: s.theme,
        // hitlRequest excluded — ephemeral
      }),
    }
  )
)
