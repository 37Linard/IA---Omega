'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Copy, Check, RefreshCw, ThumbsUp, ThumbsDown, Bot, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import { CodeBlock } from './CodeBlock'
import { ThinkingSteps } from './ThinkingSteps'
import { useChatStore } from '@/store/chatStore'
import type { Message } from '@/lib/types'

interface Props {
  message: Message
  onRegenerate?: () => void
}

function BlinkCursor() {
  return (
    <span
      className="cursor-blink"
      style={{
        display: 'inline-block',
        width: '2px',
        height: '16px',
        background: 'var(--accent)',
        borderRadius: '1px',
        marginLeft: '2px',
        verticalAlign: 'middle',
      }}
    />
  )
}

export function MessageBubble({ message, onRegenerate }: Props) {
  const [copied, setCopied] = useState(false)
  const setFeedback = useChatStore(s => s.setFeedback)
  const isUser = message.role === 'user'
  const isStreaming = message.isStreaming
  const hasContent = message.content.length > 0

  const copy = () => {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (isUser) {
    return (
      <div className="anim-fade-up flex justify-end gap-3 group">
        <div style={{ maxWidth: 'min(540px, 85%)' }}>
          <div
            style={{
              background: 'var(--user-bubble)',
              border: '1px solid var(--border-strong)',
              borderRadius: '18px 18px 4px 18px',
              padding: '12px 16px',
            }}
          >
            <div className="md-content-user">
              <ReactMarkdown remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children }) {
                    const lang = (className ?? '').replace('language-', '')
                    const code = String(children).replace(/\n$/, '')
                    if (lang || code.includes('\n')) return <CodeBlock language={lang || 'text'}>{code}</CodeBlock>
                    return <code>{children}</code>
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          </div>
        </div>
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            background: 'var(--surface-active)',
            border: '1px solid var(--border-strong)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            marginTop: '2px',
          }}
        >
          <User size={14} style={{ color: 'var(--text-secondary)' }} />
        </div>
      </div>
    )
  }

  // ─── AI message (flat, no bubble, like Claude/ChatGPT) ──────────────
  return (
    <div className="anim-fade-up flex gap-3 group">
      {/* Avatar */}
      <div
        style={{
          width: '32px',
          height: '32px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          marginTop: '2px',
          boxShadow: '0 0 0 3px var(--accent-glow)',
        }}
      >
        <Bot size={14} className="text-white" />
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0, paddingTop: '4px' }}>
        {/* Thinking steps */}
        <ThinkingSteps
          steps={message.steps}
          streamingThought={message.streamingThought}
          isStreaming={isStreaming && !hasContent}
        />

        {/* Loading dots (no content yet, no steps) */}
        {!hasContent && !message.steps.length && !message.streamingThought && isStreaming && (
          <div className="flex items-center gap-1.5 py-1">
            <span className="thinking-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--text-muted)', display: 'inline-block' }} />
            <span className="thinking-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--text-muted)', display: 'inline-block' }} />
            <span className="thinking-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--text-muted)', display: 'inline-block' }} />
          </div>
        )}

        {/* Message text */}
        {hasContent && (
          <div className="md-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children }) {
                  const lang = (className ?? '').replace('language-', '')
                  const code = String(children).replace(/\n$/, '')
                  if (lang || code.includes('\n')) return <CodeBlock language={lang || 'text'}>{code}</CodeBlock>
                  return <code>{children}</code>
                },
                table({ children }) {
                  return (
                    <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', marginTop: '12px', marginBottom: '12px' }}>
                      <table style={{ width: '100%' }}>{children}</table>
                    </div>
                  )
                },
                a({ href, children }) {
                  return <a href={href} target="_blank" rel="noreferrer">{children}</a>
                },
                img({ src, alt }) {
                  if (!src) return null
                  return (
                    <img
                      src={src}
                      alt={alt ?? ''}
                      style={{
                        maxWidth: '100%',
                        borderRadius: '8px',
                        border: '1px solid var(--border)',
                        marginTop: '8px',
                        marginBottom: '8px',
                        display: 'block',
                        boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
                      }}
                      loading="lazy"
                    />
                  )
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
            {isStreaming && <BlinkCursor />}
          </div>
        )}

        {/* Error */}
        {message.error && (
          <div
            style={{
              marginTop: '8px',
              fontSize: '13px',
              color: '#f87171',
              background: 'rgba(248,113,113,0.08)',
              border: '1px solid rgba(248,113,113,0.2)',
              borderRadius: 'var(--radius-sm)',
              padding: '8px 12px',
            }}
          >
            ⚠ {message.error}
          </div>
        )}

        {/* Actions */}
        {hasContent && !isStreaming && (
          <div
            className="flex items-center gap-0.5 mt-3 opacity-0 group-hover:opacity-100 transition-opacity duration-150"
          >
            <ActionBtn onClick={copy} title={copied ? 'Copiado!' : 'Copiar'} active={copied}>
              {copied ? <Check size={13} /> : <Copy size={13} />}
            </ActionBtn>
            {onRegenerate && (
              <ActionBtn onClick={onRegenerate} title="Regenerar resposta">
                <RefreshCw size={13} />
              </ActionBtn>
            )}
            <div style={{ width: '1px', height: '14px', background: 'var(--border)', margin: '0 4px' }} />
            <ActionBtn
              onClick={() => setFeedback(message.id, 'up')}
              title="Boa resposta"
              active={message.feedback === 'up'}
              activeColor="#4ade80"
            >
              <ThumbsUp size={13} />
            </ActionBtn>
            <ActionBtn
              onClick={() => setFeedback(message.id, 'down')}
              title="Resposta ruim"
              active={message.feedback === 'down'}
              activeColor="#f87171"
            >
              <ThumbsDown size={13} />
            </ActionBtn>

            {message.tokenUsage && (
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '8px' }}>
                {(message.tokenUsage.prompt + message.tokenUsage.completion).toLocaleString()} tokens
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function ActionBtn({
  onClick, title, children, active, activeColor
}: {
  onClick: () => void
  title: string
  children: React.ReactNode
  active?: boolean
  activeColor?: string
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        padding: '5px 7px',
        borderRadius: '6px',
        color: active ? (activeColor ?? 'var(--accent)') : 'var(--text-muted)',
        background: active ? `${activeColor ?? 'var(--accent)'}18` : 'transparent',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'all 0.12s',
      }}
      onMouseEnter={e => {
        if (!active) {
          e.currentTarget.style.color = 'var(--text-secondary)'
          e.currentTarget.style.background = 'var(--surface-hover)'
        }
      }}
      onMouseLeave={e => {
        if (!active) {
          e.currentTarget.style.color = 'var(--text-muted)'
          e.currentTarget.style.background = 'transparent'
        }
      }}
    >
      {children}
    </button>
  )
}
