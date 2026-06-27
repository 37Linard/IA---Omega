'use client'

import { useMemo } from 'react'
import { ReactFlow, Background, Controls, type Node, type Edge } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { AgentStep } from '@/lib/types'
import { X } from 'lucide-react'

const TYPE_CFG: Record<string, { color: string; bg: string; label: string }> = {
  thought:      { color: '#60a5fa', bg: '#1e3a5f',  label: 'Raciocinio'   },
  action:       { color: '#a78bfa', bg: '#2d1f5e',  label: 'Acao'         },
  observation:  { color: '#4ade80', bg: '#14432a',  label: 'Observacao'   },
  reflection:   { color: '#fb923c', bg: '#431a07',  label: 'Reflexao'     },
  error:        { color: '#f87171', bg: '#450a0a',  label: 'Erro'         },
  correction:   { color: '#fbbf24', bg: '#451a03',  label: 'Correcao'     },
  step:         { color: '#94a3b8', bg: '#1e293b',  label: 'Passo'        },
  agent_status: { color: '#818cf8', bg: '#1e1b4b',  label: 'Agente'       },
  plan:         { color: '#34d399', bg: '#064e3b',  label: 'Plano'        },
}

function buildGraph(steps: AgentStep[]): { nodes: Node[]; edges: Edge[] } {
  const agents = new Set<string>()
  steps.forEach(s => { if (s.agent) agents.add(s.agent) })
  const agentList = ['default', ...Array.from(agents)]
  const colW = 340

  const colCounters: Record<string, number> = {}
  const nodes: Node[] = []
  const edges: Edge[] = []

  steps.forEach((step, i) => {
    const agentKey = step.agent ?? 'default'
    const colIdx   = agentList.indexOf(agentKey)
    const rowIdx   = colCounters[agentKey] ?? 0
    colCounters[agentKey] = rowIdx + 1

    const cfg  = TYPE_CFG[step.type] ?? TYPE_CFG.step
    const text = step.content.length > 120 ? step.content.slice(0, 120) + '…' : step.content

    nodes.push({
      id:       step.id,
      position: { x: colIdx * colW, y: rowIdx * 110 },
      data:     {
        label: (
          <div style={{ textAlign: 'left' }}>
            <p style={{ fontSize: '9px', fontWeight: 700, color: cfg.color, letterSpacing: '0.06em', marginBottom: '4px' }}>
              {cfg.label}{step.agent ? ` · ${step.agent}` : ''}
              {step.score != null ? ` · ${step.score}/5` : ''}
            </p>
            <p style={{ fontSize: '11px', color: '#e2e8f0', lineHeight: 1.4, wordBreak: 'break-word' }}>
              {text}
            </p>
          </div>
        ),
      },
      style: {
        background: cfg.bg,
        border: `1px solid ${cfg.color}66`,
        borderRadius: '8px',
        padding: '10px 12px',
        width: colW - 40,
        boxShadow: `0 0 12px ${cfg.color}22`,
        fontSize: '12px',
      },
    })

    // Edge: conecta ao passo anterior no mesmo agente
    if (rowIdx > 0) {
      const prevId = nodes
        .slice(0, -1)
        .reverse()
        .find(n => {
          const s = steps.find(st => st.id === n.id)
          return (s?.agent ?? 'default') === agentKey
        })?.id
      if (prevId) {
        edges.push({
          id:            `e-${prevId}-${step.id}`,
          source:        prevId,
          target:        step.id,
          style:         { stroke: cfg.color + '88', strokeWidth: 1.5 },
          animated:      step.type === 'action',
        })
      }
    }
    // Edge cross-agent: agent_status links to next non-default node
    if (i > 0 && agentKey !== 'default') {
      const prevDefault = nodes
        .slice(0, -1)
        .reverse()
        .find(n => {
          const s = steps.find(st => st.id === n.id)
          return (s?.agent ?? 'default') === 'default' && s?.type === 'agent_status'
        })
      if (prevDefault && rowIdx === 0) {
        edges.push({
          id:     `e-cross-${prevDefault.id}-${step.id}`,
          source: prevDefault.id,
          target: step.id,
          style:  { stroke: '#818cf888', strokeWidth: 1, strokeDasharray: '4 3' },
        })
      }
    }
  })

  return { nodes, edges }
}

interface Props {
  steps: AgentStep[]
  onClose: () => void
}

export function ThoughtTree({ steps, onClose }: Props) {
  const { nodes, edges } = useMemo(() => buildGraph(steps), [steps])

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.7)',
        zIndex: 150,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        style={{
          background: '#0f172a',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-lg)',
          width: '100%',
          maxWidth: '1100px',
          height: '80vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 32px 80px rgba(0,0,0,0.7)',
        }}
        className="anim-fade-up"
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 20px',
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
        }}>
          <div>
            <p style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>
              NOC — Arvore de Raciocinio
            </p>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              {steps.length} passos · clique e arraste para navegar
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* Legend */}
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              {(['thought', 'action', 'observation', 'reflection', 'error'] as const).map(k => (
                <span key={k} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: TYPE_CFG[k].color }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: TYPE_CFG[k].color, display: 'inline-block' }} />
                  {TYPE_CFG[k].label}
                </span>
              ))}
            </div>
            <button
              onClick={onClose}
              style={{ color: 'var(--text-muted)', background: 'none', fontSize: '20px', cursor: 'pointer', lineHeight: 1 }}
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* React Flow */}
        <div style={{ flex: 1 }}>
          {steps.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Nenhum passo ainda — envie uma mensagem para o agente.</p>
            </div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              minZoom={0.3}
              maxZoom={2}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#334155" gap={20} size={1} />
              <Controls
                style={{
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                }}
              />
            </ReactFlow>
          )}
        </div>
      </div>
    </div>
  )
}
