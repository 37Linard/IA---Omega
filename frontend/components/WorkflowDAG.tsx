'use client'

import { useMemo } from 'react'
import { ReactFlow, Background, Controls, type Node, type Edge } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import { Loader2, CheckCircle2, XCircle, Circle } from 'lucide-react'
import type { WorkflowPlan, WorkflowNode } from '@/lib/types'
import { X } from 'lucide-react'

const NODE_W = 260
const NODE_H = 84

type Status = WorkflowNode['status'] | 'root'

const STATUS_CFG: Record<Status, { color: string; bg: string }> = {
  pending: { color: '#64748b', bg: '#1e293b' },
  running: { color: '#818cf8', bg: '#1e1b4b' },
  done:    { color: '#4ade80', bg: '#14432a' },
  error:   { color: '#f87171', bg: '#450a0a' },
  root:    { color: '#34d399', bg: '#064e3b' },
}

function StatusIcon({ status }: { status: WorkflowNode['status'] }) {
  const cfg = STATUS_CFG[status]
  if (status === 'running') return <Loader2 size={12} style={{ color: cfg.color, animation: 'spin 1s linear infinite' }} />
  if (status === 'done')    return <CheckCircle2 size={12} style={{ color: cfg.color }} />
  if (status === 'error')   return <XCircle size={12} style={{ color: cfg.color }} />
  return <Circle size={12} style={{ color: cfg.color }} />
}

function layout(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'TB', nodesep: 50, ranksep: 90 })
  g.setDefaultEdgeLabel(() => ({}))

  nodes.forEach(n => g.setNode(n.id, { width: NODE_W, height: NODE_H }))
  edges.forEach(e => g.setEdge(e.source, e.target))

  dagre.layout(g)

  return nodes.map(n => {
    const pos = g.node(n.id)
    return { ...n, position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 } }
  })
}

function makeNode(id: string, status: Status, title: string, subtitle: string, resultPreview?: string): Node {
  const cfg = STATUS_CFG[status]
  return {
    id,
    position: { x: 0, y: 0 },
    data: {
      label: (
        <div style={{ textAlign: 'left' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
            {status !== 'root' && <StatusIcon status={status} />}
            <p style={{ fontSize: '10px', fontWeight: 700, color: cfg.color, letterSpacing: '0.05em' }}>
              {title}
            </p>
          </div>
          <p style={{ fontSize: '11px', color: '#e2e8f0', lineHeight: 1.4, wordBreak: 'break-word' }}>
            {subtitle.length > 100 ? subtitle.slice(0, 100) + '…' : subtitle}
          </p>
          {resultPreview && (
            <p style={{ fontSize: '10px', color: '#94a3b8', lineHeight: 1.3, marginTop: '4px', wordBreak: 'break-word' }}>
              {resultPreview.length > 80 ? resultPreview.slice(0, 80) + '…' : resultPreview}
            </p>
          )}
        </div>
      ),
    },
    className: status === 'running' ? 'anim-pulse-glow' : undefined,
    style: {
      background: cfg.bg,
      border: `1px solid ${cfg.color}66`,
      borderRadius: '8px',
      padding: '10px 12px',
      width: NODE_W - 40,
      fontSize: '12px',
      '--pulse-color': cfg.color,
    } as React.CSSProperties,
  }
}

function buildGraph(workflow: WorkflowPlan): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = []
  const edges: Edge[] = []

  nodes.push(makeNode('root', 'root', 'TAREFA', workflow.task))

  const showAggregate = workflow.nodes.length > 1

  workflow.nodes.forEach(n => {
    const id = `spec-${n.id}`
    nodes.push(makeNode(id, n.status, n.label, n.subtask, n.status === 'done' || n.status === 'error' ? n.result : undefined))
    edges.push({
      id: `e-root-${id}`,
      source: 'root',
      target: id,
      style: { stroke: `${STATUS_CFG[n.status].color}88`, strokeWidth: 1.5 },
      animated: n.status === 'running',
    })
    if (showAggregate) {
      edges.push({
        id: `e-${id}-agg`,
        source: id,
        target: 'aggregate',
        style: { stroke: `${STATUS_CFG[n.status].color}66`, strokeWidth: 1.5 },
        animated: n.status === 'running',
      })
    }
  })

  if (showAggregate) {
    const aggStatus: Status = workflow.aggregateStatus ?? 'pending'
    nodes.push(makeNode('aggregate', aggStatus, 'AGREGADOR', 'Combina resultados dos especialistas', workflow.aggregateResult))
  }

  return { nodes: layout(nodes, edges), edges }
}

interface Props {
  workflow: WorkflowPlan | undefined
  onClose: () => void
}

export function WorkflowDAG({ workflow, onClose }: Props) {
  const { nodes, edges } = useMemo(
    () => (workflow ? buildGraph(workflow) : { nodes: [], edges: [] }),
    [workflow]
  )

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
          maxWidth: '1000px',
          height: '75vh',
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
              Workflow — Execução Paralela
            </p>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              {workflow ? `${workflow.nodes.length} especialistas em paralelo` : 'Sem workflow colaborativo nesta resposta'}
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              {(['pending', 'running', 'done', 'error'] as const).map(k => (
                <span key={k} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: STATUS_CFG[k].color }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: STATUS_CFG[k].color, display: 'inline-block' }} />
                  {k}
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
          {!workflow ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                Envie uma tarefa que precise de múltiplos especialistas (ex: &quot;pesquise X e depois salve em um arquivo&quot;) para ver o DAG.
              </p>
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
