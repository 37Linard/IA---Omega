'use client'

import { ShieldAlert, Check, X } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'

interface Props {
  onApprove: (id: string) => void
  onReject: (id: string) => void
}

export function HitlOverlay({ onApprove, onReject }: Props) {
  const hitlRequest = useChatStore(s => s.hitlRequest)
  if (!hitlRequest) return null

  const inputStr = hitlRequest.input
    ? (typeof hitlRequest.input === 'string'
        ? hitlRequest.input
        : JSON.stringify(hitlRequest.input, null, 2))
    : ''

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.7)',
        zIndex: 200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        backdropFilter: 'blur(4px)',
      }}
    >
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid #f59e0b44',
          borderRadius: 'var(--radius-lg)',
          width: '100%',
          maxWidth: '480px',
          boxShadow: '0 24px 64px rgba(0,0,0,0.6), 0 0 0 1px #f59e0b22',
          overflow: 'hidden',
        }}
        className="anim-fade-up"
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          padding: '16px 20px',
          background: 'rgba(245,158,11,0.08)',
          borderBottom: '1px solid #f59e0b33',
        }}>
          <ShieldAlert size={18} style={{ color: '#f59e0b', flexShrink: 0 }} />
          <div>
            <p style={{ fontSize: '14px', fontWeight: 700, color: '#f59e0b' }}>
              Human-in-the-Loop
            </p>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Aprovacao necessaria antes de continuar
            </p>
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <p style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>
            {hitlRequest.message}
          </p>

          <div style={{
            background: 'var(--surface-hover)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '12px',
          }}>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', letterSpacing: '0.05em', fontWeight: 600 }}>
              FERRAMENTA
            </p>
            <p style={{ fontSize: '13px', color: '#a78bfa', fontFamily: 'monospace', fontWeight: 600 }}>
              {hitlRequest.action}
            </p>
          </div>

          {inputStr && (
            <div style={{
              background: 'var(--surface-hover)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '12px',
              maxHeight: '160px',
              overflowY: 'auto',
            }}>
              <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', letterSpacing: '0.05em', fontWeight: 600 }}>
                PARAMETROS
              </p>
              <pre style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0 }}>
                {inputStr.slice(0, 600)}{inputStr.length > 600 ? '\n...' : ''}
              </pre>
            </div>
          )}

          {/* Buttons */}
          <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
            <button
              onClick={() => onReject(hitlRequest.id)}
              style={{
                flex: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                padding: '10px',
                borderRadius: '8px',
                background: 'rgba(248,113,113,0.1)',
                border: '1px solid rgba(248,113,113,0.3)',
                color: '#f87171',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(248,113,113,0.2)' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'rgba(248,113,113,0.1)' }}
            >
              <X size={14} /> Rejeitar
            </button>
            <button
              onClick={() => onApprove(hitlRequest.id)}
              style={{
                flex: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                padding: '10px',
                borderRadius: '8px',
                background: 'rgba(74,222,128,0.1)',
                border: '1px solid rgba(74,222,128,0.3)',
                color: '#4ade80',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(74,222,128,0.2)' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'rgba(74,222,128,0.1)' }}
            >
              <Check size={14} /> Aprovar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
