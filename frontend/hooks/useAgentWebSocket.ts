'use client'

import { useRef, useCallback, useState, useEffect } from 'react'
import { useChatStore } from '@/store/chatStore'
import { WS_URL, generateId } from '@/lib/utils'
import type { WsMessage } from '@/lib/types'

export function useAgentWebSocket() {
  const wsRef         = useRef<WebSocket | null>(null)
  const reconnectRef  = useRef<ReturnType<typeof setTimeout> | null>(null)
  const currentMsgId  = useRef<string | null>(null)
  const [connected, setConnected] = useState(false)
  const [running,   setRunning]   = useState(false)

  // Estável pro app inteiro (não regenera a cada reconexão) — é o que deixa
  // o backend saber "essa é a mesma conexão de antes" e retomar a stream em
  // vez de começar do zero. Não sobrevive a um reload de página de propósito
  // (fora de escopo — ver resumo do commit).
  const sessionIdRef = useRef(generateId())

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

    ws.onopen = () => {
      setConnected(true)
      // 1ª mensagem sempre — session_id estável é o que permite retomar uma
      // stream em andamento depois de reconectar (token vazio: frontend
      // ainda não tem fluxo de login, AUTH_PASSWORD não funciona pro WS
      // hoje independente disso, achado pré-existente, fora de escopo aqui)
      ws.send(JSON.stringify({ token: '', session_id: sessionIdRef.current }))
    }

    ws.onclose = () => {
      setConnected(false)
      // Só derruba "running" se não tem tarefa em andamento pra tentar
      // retomar — currentMsgId ainda setado = pode ter algo pra resumir no
      // próximo connect (hello_ack.resumed confirma ou desmente isso).
      if (!currentMsgId.current) setRunning(false)
      // schedule reconnect — always use latest connect via ref
      reconnectRef.current = setTimeout(() => connectRef.current(), 3000)
    }

    ws.onerror = () => ws.close()

    ws.onmessage = (event) => {
      try {
        const data: WsMessage = JSON.parse(event.data)

        if (data.type === 'hello_ack') {
          // não resumiu (grace period expirou, ou 1ª conexão mesmo) e tinha
          // mensagem pendurada esperando retomar — finaliza com um aviso em
          // vez de deixar o cursor piscando pra sempre
          if (!data.resumed && currentMsgId.current) {
            storeRef.current.addStep(currentMsgId.current, {
              type: 'error',
              content: 'Conexão caiu e não deu pra retomar a resposta — tente de novo.',
            })
            storeRef.current.finalizeMessage(currentMsgId.current)
            setRunning(false)
            currentMsgId.current = null
          }
          return
        }

        const msgId = currentMsgId.current
        if (!msgId) return
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
                : `[${data.agent}] ${data.status === 'error' ? 'erro' : 'concluído'}`,
              agent: data.agent,
            })
            if (data.id !== undefined) {
              s.updateWorkflowNode(msgId, data.id, data.status, data.result)
            }
            break
          case 'workflow_plan':
            s.setWorkflowPlan(msgId, data.task, data.nodes)
            break
          case 'rag_sources':
            s.addRagSources(msgId, data.sources)
            break
          case 'correction':
            s.addStep(msgId, { type: 'correction', content: data.content })
            break
          case 'reflection':
            s.addStep(msgId, {
              type:     'reflection',
              content:  data.content,
              score:    data.score,
              accepted: data.accepted,
            })
            break
          case 'reset_content':
            s.resetContent(msgId)
            break
          case 'hitl_request':
            s.setHitlRequest({ id: data.id, action: data.action, input: data.input, message: data.message })
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

  const sendTask = useCallback((
    task: string,
    templateId?: string,
    templateInputs?: Record<string, string>,
    displayLabel?: string,
  ) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return false

    storeRef.current.addUserMessage(displayLabel ?? task)
    const msgId = storeRef.current.startAssistantMessage()
    currentMsgId.current = msgId
    setRunning(true)

    const payload: Record<string, unknown> = { task }
    if (templateId) {
      payload.template_id     = templateId
      payload.template_inputs = templateInputs ?? {}
    }
    ws.send(JSON.stringify(payload))
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

  const respondHitl = useCallback((id: string, approved: boolean) => {
    wsRef.current?.send(JSON.stringify({ type: 'hitl_response', id, approved }))
    storeRef.current.setHitlRequest(null)
  }, [])

  return { connect, sendTask, cancelTask, respondHitl, connected, running }
}
