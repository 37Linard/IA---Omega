'use client'

import { useState } from 'react'
import { ChevronRight, Brain, Zap, Eye, AlertCircle, Bot, Loader2, RefreshCw, ShieldCheck, ShieldAlert } from 'lucide-react'
import type { AgentStep } from '@/lib/types'

const CFG = {
  thought:      { Icon: Brain,        label: 'Raciocínio',   color: '#818cf8', bg: 'rgba(99,102,241,0.08)', border: 'rgba(99,102,241,0.2)' },
  action:       { Icon: Zap,          label: 'Acao',         color: '#fbbf24', bg: 'rgba(251,191,36,0.08)',  border: 'rgba(251,191,36,0.2)'  },
  observation:  { Icon: Eye,          label: 'Resultado',    color: '#34d399', bg: 'rgba(52,211,153,0.08)',  border: 'rgba(52,211,153,0.2)'  },
  step:         { Icon: Bot,          label: 'Passo',        color: '#60a5fa', bg: 'rgba(96,165,250,0.08)',  border: 'rgba(96,165,250,0.2)'  },
  error:        { Icon: AlertCircle,  label: 'Erro',         color: '#f87171', bg: 'rgba(248,113,113,0.08)', border: 'rgba(248,113,113,0.2)' },
  agent_status: { Icon: Bot,          label: 'Agente',       color: '#22d3ee', bg: 'rgba(34,211,238,0.08)',  border: 'rgba(34,211,238,0.2)'  },
  plan:         { Icon: Brain,        label: 'Plano',        color: '#a78bfa', bg: 'rgba(167,139,250,0.08)', border: 'rgba(167,139,250,0.2)' },
  correction:   { Icon: RefreshCw,    label: 'Auto-correcao',color: '#fb923c', bg: 'rgba(251,146,60,0.08)',  border: 'rgba(251,146,60,0.2)'  },
  reflection:   { Icon: ShieldCheck,  label: 'Reflexao',     color: '#34d399', bg: 'rgba(52,211,153,0.08)',  border: 'rgba(52,211,153,0.2)'  },
} as const

function ScoreDots({ score }: { score: number }) {
  return (
    <span style={{ display: 'inline-flex', gap: '3px', marginLeft: '6px' }}>
      {[1, 2, 3, 4, 5].map(i => (
        <span
          key={i}
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: i <= score
              ? score >= 4 ? '#34d399' : score >= 3 ? '#fbbf24' : '#f87171'
              : 'rgba(255,255,255,0.12)',
          }}
        />
      ))}
    </span>
  )
}

function StepRow({ step }: { step: AgentStep }) {
  const [open, setOpen] = useState(false)

  const baseCfg = CFG[step.type] ?? CFG.step
  const isRejected = step.type === 'reflection' && step.accepted === false
  const color  = isRejected ? '#f87171' : baseCfg.color
  const bg     = isRejected ? 'rgba(248,113,113,0.08)' : baseCfg.bg
  const border = isRejected ? 'rgba(248,113,113,0.2)'  : baseCfg.border
  const Icon   = isRejected ? ShieldAlert : baseCfg.Icon
  const isLong = step.content.length > 100

  return (
    <div
      style={{
        background: bg,
        border: `1px solid ${border}`,
        borderRadius: '8px',
        overflow: 'hidden',
      }}
    >
      <button
        onClick={() => isLong && setOpen(o => !o)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '7px 10px',
          cursor: isLong ? 'pointer' : 'default',
          textAlign: 'left',
          background: 'transparent',
        }}
      >
        <Icon size={12} style={{ color, flexShrink: 0 }} />
        <span style={{ fontSize: '11.5px', fontWeight: 600, color, flexShrink: 0 }}>
          {baseCfg.label}
          {step.agent && ` \xb7 ${step.agent}`}
          {step.type === 'reflection' && step.score !== undefined && (
            <ScoreDots score={step.score} />
          )}
        </span>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {!isLong ? step.content : open ? '' : step.content.slice(0, 80) + '...'}
        </span>
        {isLong && (
          <ChevronRight
            size={11}
            style={{
              color: 'var(--text-muted)',
              flexShrink: 0,
              transform: open ? 'rotate(90deg)' : 'none',
              transition: 'transform 0.15s',
            }}
          />
        )}
      </button>
      {isLong && open && (
        <pre
          style={{
            fontSize: '12px',
            color: 'var(--text-secondary)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: 'monospace',
            padding: '0 10px 10px',
            lineHeight: 1.6,
            margin: 0,
          }}
        >
          {step.content}
        </pre>
      )}
    </div>
  )
}

interface Props {
  steps: AgentStep[]
  streamingThought?: string
  isStreaming?: boolean
}

export function ThinkingSteps({ steps, streamingThought, isStreaming }: Props) {
  const [open, setOpen] = useState(false)
  if (!steps.length && !streamingThought) return null

  return (
    <div style={{ marginBottom: '12px' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '12px',
          color: 'var(--text-muted)',
          background: 'transparent',
          padding: '2px 0 6px',
          transition: 'color 0.12s',
        }}
        onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
        onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
      >
        {isStreaming && !steps.length ? (
          <Loader2 size={12} style={{ color: '#818cf8', animation: 'spin 1s linear infinite' }} />
        ) : (
          <Brain size={12} style={{ color: '#818cf8' }} />
        )}
        <span style={{ fontWeight: 500 }}>
          {isStreaming && !steps.length
            ? 'Pensando...'
            : `${steps.length} passo${steps.length !== 1 ? 's' : ''}`}
        </span>
        <ChevronRight
          size={11}
          style={{
            transform: open ? 'rotate(90deg)' : 'none',
            transition: 'transform 0.15s',
          }}
        />
      </button>

      {open && (
        <div className="anim-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {steps.map(s => <StepRow key={s.id} step={s} />)}
          {streamingThought && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: CFG.thought.bg,
                border: `1px solid ${CFG.thought.border}`,
                borderRadius: '8px',
                padding: '7px 10px',
              }}
            >
              <Loader2 size={12} style={{ color: '#818cf8', animation: 'spin 1s linear infinite', flexShrink: 0 }} />
              <span style={{ fontSize: '11.5px', fontWeight: 600, color: '#818cf8', flexShrink: 0 }}>Raciocínio</span>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                {streamingThought.slice(-80)}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
