'use client'

import { useEffect, useRef } from 'react'
import { Bot, Sparkles, Zap, Code2, BookOpen, Search } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { MessageBubble } from './MessageBubble'
import { MessageInput } from './MessageInput'
import { useAgentWebSocket } from '@/hooks/useAgentWebSocket'
import { HitlOverlay } from './HitlOverlay'

const SUGGESTIONS = [
  { icon: Search, text: 'Pesquise as últimas notícias sobre IA e me faça um resumo' },
  { icon: Code2,  text: 'Escreva um script Python para organizar arquivos por extensão' },
  { icon: BookOpen, text: 'Me crie um plano de estudos para aprender React em 30 dias' },
  { icon: Zap,    text: 'Qual a cotação do dólar agora e compare com o euro?' },
]

export function ChatArea() {
  const store = useChatStore()
  const conv  = store.getActive()
  const bottomRef   = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const autoScroll  = useRef(true)

  const { connect, sendTask, cancelTask, respondHitl, connected, running } = useAgentWebSocket()
  const pendingTemplateTask    = useChatStore(s => s.pendingTemplateTask)
  const setPendingTemplateTask = useChatStore(s => s.setPendingTemplateTask)

  useEffect(() => { connect() }, [connect])

  useEffect(() => {
    if (!connected || !pendingTemplateTask || running) return
    const { task, templateId, templateInputs, displayLabel } = pendingTemplateTask
    setPendingTemplateTask(null)
    autoScroll.current = true
    sendTask(task, templateId, templateInputs, displayLabel)
  }, [connected, pendingTemplateTask, running, sendTask, setPendingTemplateTask])

  useEffect(() => {
    if (autoScroll.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  })

  const handleScroll = () => {
    const el = containerRef.current
    if (!el) return
    autoScroll.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100
  }

  const handleSend = (text: string) => {
    if (!conv) store.newConversation()
    autoScroll.current = true
    sendTask(text)
  }

  const messages = conv?.messages ?? []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--chat-bg)' }}>
      {/* Messages */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
        }}
      >
        {messages.length === 0 ? (
          <EmptyState onSuggestion={handleSend} connected={connected} />
        ) : (
          <div
            style={{
              maxWidth: '760px',
              margin: '0 auto',
              padding: '32px 24px 16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '24px',
            }}
          >
            {messages.map((msg, i) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onRegenerate={
                  msg.role === 'assistant' && i === messages.length - 1 && !running
                    ? () => {
                        const prev = messages[i - 1]
                        if (prev?.role === 'user') handleSend(prev.content)
                      }
                    : undefined
                }
              />
            ))}
            <div ref={bottomRef} style={{ height: '4px' }} />
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{ maxWidth: '760px', margin: '0 auto', width: '100%' }}>
        <MessageInput
          onSend={handleSend}
          onCancel={cancelTask}
          running={running}
          connected={connected}
        />
      </div>

      <HitlOverlay
        onApprove={(id) => respondHitl(id, true)}
        onReject={(id) => respondHitl(id, false)}
      />
    </div>
  )
}

function EmptyState({
  onSuggestion,
  connected,
}: {
  onSuggestion: (s: string) => void
  connected: boolean
}) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100%',
        padding: '48px 24px',
        textAlign: 'center',
      }}
    >
      {/* Logo */}
      <div
        style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '24px',
          boxShadow: '0 0 0 8px var(--accent-glow), 0 8px 32px rgba(99,102,241,0.3)',
        }}
      >
        <Bot size={28} className="text-white" />
      </div>

      <h1
        style={{
          fontSize: '26px',
          fontWeight: 650,
          color: 'var(--text-primary)',
          marginBottom: '10px',
          letterSpacing: '-0.3px',
        }}
      >
        Como posso ajudar?
      </h1>
      <p style={{ fontSize: '15px', color: 'var(--text-muted)', maxWidth: '400px', lineHeight: 1.6, marginBottom: '36px' }}>
        Pesquiso, codifico, analiso e executo tarefas locais — tudo com ferramentas reais.
      </p>

      {!connected && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '13px',
            color: '#fbbf24',
            background: 'rgba(251,191,36,0.08)',
            border: '1px solid rgba(251,191,36,0.2)',
            borderRadius: 'var(--radius-sm)',
            padding: '8px 16px',
            marginBottom: '24px',
          }}
        >
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#fbbf24', animation: 'pulse 1.5s ease-in-out infinite', display: 'inline-block' }} />
          Conectando ao servidor local...
        </div>
      )}

      {/* Suggestions grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '10px',
          maxWidth: '600px',
          width: '100%',
        }}
      >
        {SUGGESTIONS.map(({ icon: Icon, text }) => (
          <button
            key={text}
            onClick={() => onSuggestion(text)}
            disabled={!connected}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              textAlign: 'left',
              padding: '14px 16px',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              cursor: connected ? 'pointer' : 'not-allowed',
              opacity: connected ? 1 : 0.45,
              transition: 'border-color 0.15s, background 0.15s',
              fontSize: '13.5px',
              color: 'var(--text-secondary)',
              lineHeight: 1.5,
            }}
            onMouseEnter={e => {
              if (!connected) return
              e.currentTarget.style.borderColor = 'rgba(99,102,241,0.35)'
              e.currentTarget.style.background = 'var(--surface-hover)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = 'var(--border)'
              e.currentTarget.style.background = 'var(--surface)'
            }}
          >
            <Icon size={15} style={{ color: 'var(--accent)', marginTop: '1px', flexShrink: 0 }} />
            {text}
          </button>
        ))}
      </div>
    </div>
  )
}
