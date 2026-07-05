'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronRight, Brain, Zap, Eye, AlertCircle, Bot, Loader2, RefreshCw, ShieldCheck, ShieldAlert, Search, Globe } from 'lucide-react'
import type { AgentStep } from '@/lib/types'
import { parseActionCall, countSearchResults, hostnameOf } from '@/lib/sources'

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

function SearchStepRow({ query, count }: { step: AgentStep; query: string; count?: number }) {
  const pending = count === undefined
  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', gap: '8px',
        background: 'rgba(34,211,238,0.08)', border: '1px solid rgba(34,211,238,0.2)',
        borderRadius: '8px', padding: '7px 10px',
      }}
    >
      {pending
        ? <Loader2 size={12} style={{ color: '#22d3ee', flexShrink: 0, animation: 'spin 1s linear infinite' }} />
        : <Search size={12} style={{ color: '#22d3ee', flexShrink: 0 }} />}
      <span style={{ fontSize: '11.5px', fontWeight: 600, color: '#22d3ee', flexShrink: 0 }}>
        {pending ? 'Pesquisando na web' : 'Pesquisado na web'}
      </span>
      <span style={{ fontSize: '12px', color: 'var(--text-muted)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {query}
      </span>
      {!pending && (
        <span style={{ fontSize: '10.5px', color: '#22d3ee', background: 'rgba(34,211,238,0.15)', borderRadius: '99px', padding: '1px 7px', flexShrink: 0 }}>
          {count}
        </span>
      )}
    </div>
  )
}

function OpenPageStepRow({ url, hostname, pending }: { url: string; hostname: string; pending: boolean }) {
  const Tag = pending ? 'div' : 'a'
  return (
    <Tag
      {...(pending ? {} : { href: url, target: '_blank', rel: 'noreferrer' })}
      style={{
        display: 'flex', alignItems: 'center', gap: '8px', textDecoration: 'none',
        background: 'rgba(167,139,250,0.08)', border: '1px solid rgba(167,139,250,0.2)',
        borderRadius: '8px', padding: '7px 10px',
      }}
    >
      {pending
        ? <Loader2 size={12} style={{ color: '#a78bfa', flexShrink: 0, animation: 'spin 1s linear infinite' }} />
        : <Globe size={12} style={{ color: '#a78bfa', flexShrink: 0 }} />}
      <span style={{ fontSize: '11.5px', fontWeight: 600, color: '#a78bfa', flexShrink: 0 }}>
        {pending ? 'Abrindo página' : 'Página aberta'}
      </span>
      <span style={{ fontSize: '12px', color: 'var(--text-muted)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {hostname}
      </span>
    </Tag>
  )
}

type RenderItem =
  | { kind: 'search'; step: AgentStep; query: string; count?: number }
  | { kind: 'open'; step: AgentStep; url: string; hostname: string; pending: boolean }
  | { kind: 'default'; step: AgentStep }

function buildRenderItems(steps: AgentStep[]): RenderItem[] {
  const items: RenderItem[] = []
  const skip = new Set<number>()

  steps.forEach((step, i) => {
    if (skip.has(i)) return
    if (step.type === 'action') {
      const parsed = parseActionCall(step.content)
      const nextObs = steps[i + 1]

      if (parsed?.tool === 'web_search') {
        const query = typeof parsed.input.query === 'string' ? parsed.input.query : step.content
        const count = nextObs?.type === 'observation' ? countSearchResults(nextObs.content) : undefined
        if (nextObs?.type === 'observation') skip.add(i + 1)
        items.push({ kind: 'search', step, query, count })
        return
      }
      if (parsed?.tool === 'fetch_page') {
        const url = typeof parsed.input.url === 'string' ? parsed.input.url : ''
        const pending = nextObs?.type !== 'observation'
        if (nextObs?.type === 'observation') skip.add(i + 1)
        items.push({ kind: 'open', step, url, hostname: hostnameOf(url), pending })
        return
      }
    }
    items.push({ kind: 'default', step })
  })

  return items
}

interface Props {
  steps: AgentStep[]
  streamingThought?: string
  isStreaming?: boolean
}

export function ThinkingSteps({ steps, streamingThought, isStreaming }: Props) {
  const [open, setOpen] = useState(false)
  const userToggled = useRef(false)
  const items = useMemo(() => buildRenderItems(steps), [steps])

  // Enquanto a IA esta pesquisando, abre sozinho pra mostrar o processo ao vivo;
  // ao terminar, recolhe de volta — a nao ser que o usuario ja tenha mexido no toggle.
  useEffect(() => {
    if (!userToggled.current) setOpen(isStreaming ?? false)
  }, [isStreaming])

  if (!steps.length && !streamingThought) return null

  return (
    <div style={{ marginBottom: '12px' }}>
      <button
        onClick={() => { userToggled.current = true; setOpen(o => !o) }}
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
          {items.map(item =>
            item.kind === 'search' ? <SearchStepRow key={item.step.id} step={item.step} query={item.query} count={item.count} />
            : item.kind === 'open' ? <OpenPageStepRow key={item.step.id} url={item.url} hostname={item.hostname} pending={item.pending} />
            : <StepRow key={item.step.id} step={item.step} />
          )}
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
