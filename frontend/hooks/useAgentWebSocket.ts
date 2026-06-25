'use client'

import { useRef, useCallback, useState, useEffect } from 'react'
import { useChatStore } from '@/store/chatStore'
import { WS_URL } from '@/lib/utils'
import type { WsMessage } from '@/lib/types'

export function useAgentWebSocket() {
  const wsRef         = useRef<WebSocket | null>(null)
  const reconnectRef  = useRef<ReturnType<typeof setTimeout> | null>(null)
  const currentMsgId  = useRef<string | null>(null)
  const [connected, setConnected] = useState(false)
  const [running,   setRunning]   = useState(false)

  // Stable ref to store so callbacks don't become stale
  const store      = useChatStore()
  const storeRef   = useRef(store)
  useEffect(() => { storeRef.current = store })

  const connect = useCallback(() => {
    const state = wsRef.current?.readyState
    // Guard BOTH open and connecting — prevents double connections
    if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) return

    if (reconnectRef.current) {
      clearTimeout(reconnectRef.current)
      reconnectRef.current = null
    }

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onclose = () => {
      setConnected(false)
      setRunning(false)
      // schedule reconnect — always use latest connect via ref
      reconnectRef.current = setTimeout(() => connectRef.current(), 3000)
    }

    ws.onerror = () => ws.close()

    ws.onmessage = (event) => {
      const msgId = currentMsgId.current
      if (!msgId) return
      try {
        const data: WsMessage = JSON.parse(event.data)
        const s = storeRef.current

        switch (data.type) {
          case 'token':
            s.appendToken(msgId, data.content)
            break
          case 'final_stream_start':
            s.addStep(msgId, { type: 'thought', content: '' })
            break
          case 'final_token':
            s.appendFinalToken(msgId, data.content)
            break
          case 'final':
            s.finalizeMessage(msgId, data.content)
            break
          case 'thought':
            s.addStep(msgId, { type: 'thought', content: data.content })
            break
          case 'action':
            s.addStep(msgId, { type: 'action', content: data.content })
            break
          case 'observation':
            s.addStep(msgId, { type: 'observation', content: data.content })
            break
          case 'step':
            s.addStep(msgId, { type: 'step', content: data.content })
            break
          case 'error':
            s.addStep(msgId, { type: 'error', content: data.content })
            break
          case 'agent_status':
            s.addStep(msgId, {
              type:    'agent_status',
              content: data.status === 'running'
                ? `[${data.agent}] ${data.subtask ?? ''}`
                : `[${data.agent}] concluído`,
              agent: data.agent,
            })
            break
          case 'token_usage':
            s.setTokenUsage(msgId, data.prompt, data.completion)
            break
          case 'done':
            s.finalizeMessage(msgId)
            setRunning(false)
            currentMsgId.current = null
            break
        }
      } catch {
        // ignore parse errors
      }
    }
  }, []) // stable — no deps

  // Stable ref so onclose closure always calls latest connect
  const connectRef = useRef(connect)
  useEffect(() => { connectRef.current = connect }, [connect])

  const sendTask = useCallback((task: string) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return false

    storeRef.current.addUserMessage(task)
    const msgId = storeRef.current.startAssistantMessage()
    currentMsgId.current = msgId
    setRunning(true)

    ws.send(JSON.stringify({ task }))
    return true
  }, [])

  const cancelTask = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: 'cancel' }))
    if (currentMsgId.current) {
      storeRef.current.finalizeMessage(currentMsgId.current)
    }
    setRunning(false)
    currentMsgId.current = null
  }, [])

  return { connect, sendTask, cancelTask, connected, running }
}
