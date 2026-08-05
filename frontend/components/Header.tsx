'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Menu, Sun, Moon, User, Heart, Cpu, Database, Trash2, FolderOpen, RefreshCw, CheckCircle, XCircle, Loader2, Layers, GitGraph, LayoutGrid, Workflow, Download, ScrollText, MoreHorizontal, Puzzle } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { fetchModels, setModel, fetchProfile, saveProfile, fetchRagDocs, ragIndexFolder, ragDeleteDoc, uploadFile, fetchMetrics, fetchSandboxStatus, fetchSpecialistModels, setSpecialistModel, exportConversation, fetchHealth, fetchAudit, fetchTraceRecent, searchPlugins, stagePlugin, fetchStagedPlugins, fetchStagedPluginCode, approvePlugin, fetchPluginRegistries, addPluginRegistry, removePluginRegistry, fetchTrustedAuthors, trustPluginAuthor, untrustPluginAuthor } from '@/lib/api'
import type { AuditEntry, TraceSpan, PluginSearchResult, StagedPlugin, TrustedAuthor } from '@/lib/api'
import { ThoughtTree } from './ThoughtTree'
import { WorkflowDAG } from './WorkflowDAG'
import { CodeBlock } from './CodeBlock'
import type { UserProfile } from '@/lib/types'
import { useRouter } from 'next/navigation'

interface Props { onToggleSidebar: () => void }

export function Header({ onToggleSidebar }: Props) {
  const { theme, toggleTheme, getActive } = useChatStore()
  const router = useRouter()
  const conv = getActive()
  const [models, setModels] = useState<string[]>([])
  const [currentModel, setCurrentModel] = useState('')
  const [profileOpen, setProfileOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const [healthOpen, setHealthOpen] = useState(false)
  const [auditOpen, setAuditOpen] = useState(false)
  const [ragOpen, setRagOpen] = useState(false)
  const [modelsOpen, setModelsOpen] = useState(false)
  const [nocOpen,    setNocOpen]    = useState(false)
  const [workflowOpen, setWorkflowOpen] = useState(false)
  const [pluginsOpen, setPluginsOpen] = useState(false)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [exportState, setExportState] = useState<'idle' | 'saving' | 'done' | 'error'>('idle')

  useEffect(() => {
    fetchModels().then(d => { setModels(d.models); setCurrentModel(d.current) }).catch(() => {})
    fetchProfile().then(setProfile).catch(() => {})
  }, [])

  const changeModel = async (m: string) => {
    setCurrentModel(m)
    try { await setModel(m) } catch {}
  }

  const handleExport = async () => {
    if (!conv || conv.messages.length === 0 || exportState === 'saving') return
    setExportState('saving')
    try {
      const messages = conv.messages
        .filter(m => m.content.trim())
        .map(m => ({ role: m.role, content: m.content }))
      const res = await exportConversation(conv.title || 'Conversa', messages)

      // download local sempre — funciona mesmo sem Obsidian configurado
      const blob = new Blob([res.markdown], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = res.filename
      a.click()
      URL.revokeObjectURL(url)

      setExportState('done')
    } catch {
      setExportState('error')
    } finally {
      setTimeout(() => setExportState('idle'), 2500)
    }
  }

  return (
    <>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '10px 16px',
          background: 'var(--sidebar-bg)',
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
          minHeight: '52px',
        }}
      >
        {/* Mobile menu toggle */}
        <button
          onClick={onToggleSidebar}
          className="lg:hidden"
          style={iconBtnStyle}
          onMouseEnter={e => applyHover(e, true)}
          onMouseLeave={e => applyHover(e, false)}
        >
          <Menu size={17} />
        </button>

        {/* Conversation title */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {conv?.title && conv.title !== 'Nova conversa' && (
            <p style={{ fontSize: '13.5px', fontWeight: 500, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {conv.title}
            </p>
          )}
        </div>

        {/* Right controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {/* Model selector */}
          {models.length > 0 && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '5px 10px',
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                marginRight: '4px',
              }}
            >
              <Cpu size={12} style={{ color: 'var(--accent)', flexShrink: 0 }} />
              <select
                value={currentModel}
                onChange={e => changeModel(e.target.value)}
                style={{
                  background: 'transparent',
                  color: 'var(--text-secondary)',
                  fontSize: '12px',
                  outline: 'none',
                  cursor: 'pointer',
                  maxWidth: '140px',
                }}
              >
                {models.map(m => (
                  <option key={m} value={m} style={{ background: '#1a1a1a' }}>{m}</option>
                ))}
              </select>
            </div>
          )}

          {/* Colapsáveis — visíveis a partir de sm (640px); em telas
              menores só via o botão "mais". iconBtnStyle define
              display:'flex' inline no HeaderBtn, por isso o toggle de
              visibilidade fica no wrapper (classe Tailwind), não no botão
              em si — inline style sempre vence classe CSS em especificidade. */}
          <div className="hidden sm:flex" style={{ alignItems: 'center', gap: '4px' }}>
            <HeaderBtn onClick={() => router.push('/ferramentas')} title="Ferramentas IA — 25 ferramentas especializadas">
              <LayoutGrid size={15} />
            </HeaderBtn>

            <HeaderBtn
              onClick={handleExport}
              title={
                exportState === 'done' ? 'Exportado! (baixado + salvo no Obsidian se configurado)'
                : exportState === 'error' ? 'Erro ao exportar — backend disponível?'
                : 'Exportar conversa (Markdown + Obsidian)'
              }
            >
              {exportState === 'saving' ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />
                : exportState === 'done' ? <CheckCircle size={15} style={{ color: '#4ade80' }} />
                : exportState === 'error' ? <XCircle size={15} style={{ color: '#f87171' }} />
                : <Download size={15} />}
            </HeaderBtn>

            <HeaderBtn onClick={() => setNocOpen(true)} title="NOC — Arvore de Raciocinio">
              <GitGraph size={15} />
            </HeaderBtn>

            <HeaderBtn onClick={() => setWorkflowOpen(true)} title="Workflow — DAG de Execução Paralela">
              <Workflow size={15} />
            </HeaderBtn>

            <HeaderBtn onClick={() => setModelsOpen(true)} title="Modelos por Especialista">
              <Layers size={15} />
            </HeaderBtn>

            <HeaderBtn onClick={() => setRagOpen(true)} title="Indexação de documentos (RAG)">
              <Database size={15} />
            </HeaderBtn>

            <HeaderBtn onClick={() => setProfileOpen(true)} title="Perfil">
              <User size={15} />
            </HeaderBtn>

            <HeaderBtn onClick={() => setAuditOpen(true)} title="Audit log / Tracing">
              <ScrollText size={15} />
            </HeaderBtn>

            <HeaderBtn onClick={() => setPluginsOpen(true)} title="Plugin Marketplace">
              <Puzzle size={15} />
            </HeaderBtn>
          </div>

          {/* Botão "mais" — só abaixo de sm, abre menu com as 9 ações acima */}
          <div className="sm:hidden" style={{ position: 'relative' }}>
            <HeaderBtn onClick={() => setMoreOpen(o => !o)} title="Mais opções">
              <MoreHorizontal size={15} />
            </HeaderBtn>
            {moreOpen && (
              <MoreMenu
                onClose={() => setMoreOpen(false)}
                items={[
                  { icon: <LayoutGrid size={15} />, label: 'Ferramentas IA', onClick: () => router.push('/ferramentas') },
                  { icon: <Download size={15} />, label: 'Exportar conversa', onClick: handleExport },
                  { icon: <GitGraph size={15} />, label: 'NOC — Árvore de Raciocínio', onClick: () => setNocOpen(true) },
                  { icon: <Workflow size={15} />, label: 'Workflow — DAG', onClick: () => setWorkflowOpen(true) },
                  { icon: <Layers size={15} />, label: 'Modelos por Especialista', onClick: () => setModelsOpen(true) },
                  { icon: <Database size={15} />, label: 'RAG — Documentos', onClick: () => setRagOpen(true) },
                  { icon: <User size={15} />, label: 'Perfil', onClick: () => setProfileOpen(true) },
                  { icon: <ScrollText size={15} />, label: 'Audit log / Tracing', onClick: () => setAuditOpen(true) },
                  { icon: <Puzzle size={15} />, label: 'Plugin Marketplace', onClick: () => setPluginsOpen(true) },
                ]}
              />
            )}
          </div>

          <HeaderBtn onClick={() => setHealthOpen(true)} title="Status do sistema">
            <Heart size={15} />
          </HeaderBtn>

          <HeaderBtn onClick={toggleTheme} title={theme === 'dark' ? 'Tema claro' : 'Tema escuro'}>
            {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
          </HeaderBtn>
        </div>
      </header>

      {nocOpen && (
        <ThoughtTree
          steps={(conv?.messages.filter(m => m.role === 'assistant').at(-1)?.steps) ?? []}
          onClose={() => setNocOpen(false)}
        />
      )}
      {workflowOpen && (
        <WorkflowDAG
          workflow={conv?.messages.filter(m => m.role === 'assistant').at(-1)?.workflow}
          onClose={() => setWorkflowOpen(false)}
        />
      )}
      {modelsOpen && <SpecialistModelsModal models={models} onClose={() => setModelsOpen(false)} />}
      {auditOpen && <AuditLogModal onClose={() => setAuditOpen(false)} />}
      {pluginsOpen && <PluginMarketplaceModal onClose={() => setPluginsOpen(false)} />}
      {ragOpen && <RagModal onClose={() => setRagOpen(false)} />}
      {profileOpen && profile && (
        <ProfileModal profile={profile} onSave={async d => { const u = await saveProfile(d); setProfile(u); setProfileOpen(false) }} onClose={() => setProfileOpen(false)} />
      )}
      {healthOpen && <HealthModal onClose={() => setHealthOpen(false)} />}
    </>
  )
}

function HeaderBtn({ onClick, title, children }: { onClick: () => void; title: string; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={iconBtnStyle}
      onMouseEnter={e => applyHover(e, true)}
      onMouseLeave={e => applyHover(e, false)}
    >
      {children}
    </button>
  )
}

const iconBtnStyle: React.CSSProperties = {
  padding: '6px',
  borderRadius: '8px',
  color: 'var(--text-muted)',
  background: 'transparent',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  transition: 'all 0.12s',
}
function applyHover(e: React.MouseEvent<HTMLButtonElement>, on: boolean) {
  e.currentTarget.style.color    = on ? 'var(--text-primary)' : 'var(--text-muted)'
  e.currentTarget.style.background = on ? 'var(--surface-hover)' : 'transparent'
}

function MoreMenu({ items, onClose }: { items: { icon: React.ReactNode; label: string; onClick: () => void }[]; onClose: () => void }) {
  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 59 }} />
      <div
        role="menu"
        aria-label="Mais opções"
        style={{
          position: 'absolute',
          top: '100%',
          right: 0,
          marginTop: '6px',
          background: 'var(--surface)',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-sm)',
          boxShadow: '0 12px 32px rgba(0,0,0,0.4)',
          zIndex: 60,
          minWidth: '220px',
          overflow: 'hidden',
        }}
        className="anim-fade-up"
      >
        {items.map((item, i) => (
          <button
            key={i}
            onClick={() => { item.onClick(); onClose() }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              width: '100%',
              padding: '10px 14px',
              fontSize: '13px',
              color: 'var(--text-secondary)',
              background: 'transparent',
              textAlign: 'left',
              cursor: 'pointer',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </div>
    </>
  )
}

/* ── Modal base ──────────────────────────────────────────────── */
function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-lg)',
          width: '100%',
          maxWidth: '380px',
          overflow: 'hidden',
          boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
        }}
        className="anim-fade-up"
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
          <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>{title}</span>
          <button onClick={onClose} style={{ color: 'var(--text-muted)', background: 'none', fontSize: '18px', lineHeight: 1, cursor: 'pointer' }}>×</button>
        </div>
        <div style={{ padding: '20px' }}>{children}</div>
      </div>
    </div>
  )
}

function ProfileModal({ profile, onSave, onClose }: { profile: UserProfile; onSave: (d: Partial<UserProfile>) => Promise<void>; onClose: () => void }) {
  const [form, setForm] = useState({ ...profile })
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    try { await onSave(form) } finally { setSaving(false) }
  }

  return (
    <Modal title="👤 Perfil do Usuário" onClose={onClose}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <Field label="Nome (opcional)">
          <input
            value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            placeholder="Seu nome"
            style={inputStyle}
          />
        </Field>
        <Field label="Nível técnico">
          <select
            value={form.tech_level}
            disabled={form.tech_level_auto}
            onChange={e => setForm(f => ({ ...f, tech_level: e.target.value as UserProfile['tech_level'] }))}
            style={{ ...inputStyle, opacity: form.tech_level_auto ? 0.6 : 1 }}
          >
            {(['iniciante', 'intermediário', 'avançado', 'especialista'] as const).map(v => (
              <option key={v} value={v} style={{ background: '#2a2a2a' }}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>
            ))}
          </select>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '6px', fontSize: '12px', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={form.tech_level_auto}
              onChange={e => setForm(f => ({ ...f, tech_level_auto: e.target.checked }))}
            />
            Detectar automaticamente pelo que eu escrevo
          </label>
        </Field>
        <Field label="Tom de resposta">
          <select value={form.tone} onChange={e => setForm(f => ({ ...f, tone: e.target.value as UserProfile['tone'] }))} style={inputStyle}>
            {(['informal', 'neutro', 'formal', 'técnico'] as const).map(v => (
              <option key={v} value={v} style={{ background: '#2a2a2a' }}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>
            ))}
          </select>
        </Field>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
          A IA adapta linguagem e profundidade ao seu perfil automaticamente.
        </p>
        <button
          onClick={save}
          disabled={saving}
          style={{
            padding: '10px',
            background: 'var(--accent)',
            color: '#fff',
            borderRadius: 'var(--radius-sm)',
            fontSize: '14px',
            fontWeight: 500,
            cursor: saving ? 'not-allowed' : 'pointer',
            opacity: saving ? 0.7 : 1,
            transition: 'opacity 0.12s',
          }}
        >
          {saving ? 'Salvando...' : 'Salvar'}
        </button>
      </div>
    </Modal>
  )
}

type Metrics = Awaited<ReturnType<typeof fetchMetrics>>

type SandboxStatus = { mode: 'wasm' | 'docker' | 'local'; docker: boolean; image: string | null; custom?: boolean; warning: string | null }

function HealthModal({ onClose }: { onClose: () => void }) {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [sandbox, setSandbox] = useState<SandboxStatus | null>(null)
  const [securityWarnings, setSecurityWarnings] = useState<string[]>([])
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    try {
      const [m, s, h] = await Promise.all([fetchMetrics(), fetchSandboxStatus(), fetchHealth()])
      setMetrics(m)
      setSandbox(s)
      setSecurityWarnings(h.security.warnings)
      setError(false)
    }
    catch { setError(true) }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 8000)
    return () => clearInterval(id)
  }, [load])

  const inf = metrics?.inference
  const vram = metrics?.vram
  const tools = metrics?.tools ?? []
  const llmCalls = metrics?.llm_calls ?? []
  const reflection = metrics?.reflection
  const kg = metrics?.knowledge_graph
  const breakers = (metrics?.circuit_breaker ?? []).filter(b => b.open)
  // Alerta só com volume mínimo de chamadas — 1 falha isolada não é sinal de nada
  const ALERT_MIN_CALLS = 3
  const toolAlerts  = tools.filter(t => t.calls >= ALERT_MIN_CALLS && t.success_rate < 70)
  const modelAlerts = llmCalls.filter(m => m.calls >= ALERT_MIN_CALLS && m.error_rate > 20)

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-lg)',
          width: '100%',
          maxWidth: '500px',
          maxHeight: '85vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
        }}
        className="anim-fade-up"
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Heart size={14} style={{ color: '#f87171' }} />
            <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>Dashboard de Performance</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>auto-refresh 8s</span>
            <button onClick={onClose} style={{ color: 'var(--text-muted)', background: 'none', fontSize: '18px', cursor: 'pointer' }}>×</button>
          </div>
        </div>

        <div style={{ overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {error && (
            <p style={{ fontSize: '13px', color: '#f87171', textAlign: 'center' }}>Backend indisponível</p>
          )}

          {/* Segurança — AUTH_PASSWORD/JWT_SECRET, relevante pra acesso remoto (Tailscale/LAN) */}
          {securityWarnings.length > 0 && (
            <div>
              <p style={{ fontSize: '12px', fontWeight: 500, color: '#f87171', marginBottom: '10px', letterSpacing: '0.05em' }}>⚠ SEGURANÇA</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {securityWarnings.map((w, i) => (
                  <p key={i} style={{ fontSize: '12px', color: '#f87171', background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: '6px', padding: '8px 12px', lineHeight: 1.5, margin: 0 }}>
                    {w}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Circuit breaker — só aparece quando alguma tool está desabilitada */}
          {breakers.length > 0 && (
            <div>
              <p style={{ fontSize: '12px', fontWeight: 500, color: '#f87171', marginBottom: '10px', letterSpacing: '0.05em' }}>⚠ FERRAMENTAS DESABILITADAS (CIRCUIT BREAKER)</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {breakers.map(b => (
                  <div key={b.tool} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: '6px', padding: '8px 12px' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-primary)', fontFamily: 'monospace' }}>{b.tool}</span>
                    <span style={{ fontSize: '11px', color: '#f87171' }}>{b.failures} falhas — volta em {Math.round(b.cooldown_remaining_s)}s</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Taxa de erro alta — tools/modelos com volume mínimo de chamadas */}
          {(toolAlerts.length > 0 || modelAlerts.length > 0) && (
            <div>
              <p style={{ fontSize: '12px', fontWeight: 500, color: '#f87171', marginBottom: '10px', letterSpacing: '0.05em' }}>⚠ TAXA DE ERRO ALTA</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {toolAlerts.map(t => (
                  <div key={`tool-${t.tool}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: '6px', padding: '8px 12px' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-primary)', fontFamily: 'monospace' }}>{t.tool}</span>
                    <span style={{ fontSize: '11px', color: '#f87171' }}>{t.success_rate}% sucesso em {t.calls} chamadas (7d)</span>
                  </div>
                ))}
                {modelAlerts.map(m => (
                  <div key={`model-${m.model}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: '6px', padding: '8px 12px' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-primary)', fontFamily: 'monospace' }}>{m.model}</span>
                    <span style={{ fontSize: '11px', color: '#f87171' }}>{m.error_rate}% erro em {m.calls} chamadas (24h)</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Inference metrics */}
          <div>
            <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)', marginBottom: '10px', letterSpacing: '0.05em' }}>INFERÊNCIA</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
              <MetricCard label="Tokens/s" value={inf ? `${inf.tps}` : '—'} unit="TPS" color="#4ade80" />
              <MetricCard label="1º Token" value={inf ? `${inf.ttft_ms}` : '—'} unit="ms" color="#60a5fa" />
              <MetricCard label="Contexto" value={inf ? `${inf.context_pct}` : '—'} unit="%" color={inf && inf.context_pct > 80 ? '#f87171' : '#a78bfa'} />
            </div>
            {inf && (
              <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px', textAlign: 'right' }}>
                {inf.prompt_tokens} prompt + {inf.completion_tokens} completion tokens na sessão
              </p>
            )}
          </div>

          {/* Reflection — taxa de reescrita do critic (score < threshold na 1ª tentativa) */}
          {reflection && reflection.total > 0 && (
            <div>
              <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)', marginBottom: '10px', letterSpacing: '0.05em' }}>REFLECTION (7d)</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                <MetricCard label="Reescritas" value={`${reflection.rewrite_rate}`} unit="%" color={reflection.rewrite_rate > 30 ? '#f87171' : '#4ade80'} />
                <MetricCard label="Score médio" value={`${reflection.avg_score}`} unit="/ 5" color="#a78bfa" />
                <MetricCard label="Avaliações" value={`${reflection.total}`} unit="total" color="#60a5fa" />
              </div>
            </div>
          )}

          {/* VRAM */}
          {vram && vram.total_mb > 0 && (
            <div>
              <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)', marginBottom: '10px', letterSpacing: '0.05em' }}>VRAM — GPU</p>
              <div style={{ background: 'var(--surface-hover)', borderRadius: '6px', height: '8px', overflow: 'hidden', marginBottom: '6px' }}>
                <div style={{
                  height: '100%',
                  width: `${vram.pct}%`,
                  background: vram.pct > 90 ? '#f87171' : vram.pct > 75 ? '#fbbf24' : '#4ade80',
                  transition: 'width 0.5s ease',
                }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
                <span>{vram.used_mb} MB usados</span>
                <span style={{ color: vram.pct > 90 ? '#f87171' : 'var(--text-muted)' }}>{vram.pct}% de {vram.total_mb} MB</span>
                <span>{vram.free_mb} MB livres</span>
              </div>
            </div>
          )}

          {/* Sandbox status */}
          {sandbox && (() => {
            const dotColor = sandbox.mode === 'wasm' ? '#4ade80'
              : sandbox.mode === 'docker' ? (sandbox.custom ? '#4ade80' : '#fbbf24')
              : '#f87171'
            const label = sandbox.mode === 'wasm' ? 'WASM sandbox (wasmtime) — boot instantâneo'
              : sandbox.mode === 'docker' ? (sandbox.custom ? 'Docker isolado (ia-sandbox)' : 'Docker isolado (python:3.12-slim)')
              : 'Execução local (sem isolamento)'
            return (
              <div>
                <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)', marginBottom: '10px', letterSpacing: '0.05em' }}>SANDBOX — run_python</p>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  background: 'var(--surface-hover)', borderRadius: '8px', padding: '10px 14px',
                  border: `1px solid ${dotColor}30`,
                }}>
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0, background: dotColor }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 500 }}>{label}</p>
                    {sandbox.image && (
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'monospace', marginTop: '2px' }}>{sandbox.image}</p>
                    )}
                    {sandbox.warning && (
                      <p style={{ fontSize: '11px', color: '#fbbf24', marginTop: '4px', lineHeight: 1.4 }}>{sandbox.warning}</p>
                    )}
                    {!sandbox.warning && sandbox.mode === 'docker' && sandbox.custom && (
                      <p style={{ fontSize: '11px', color: '#4ade80', marginTop: '2px' }}>numpy · pandas · matplotlib · scipy disponíveis</p>
                    )}
                    {sandbox.mode === 'wasm' && (
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>stdlib apenas — sem numpy/pandas (use Docker pra libs pesadas)</p>
                    )}
                  </div>
                </div>
              </div>
            )
          })()}

          {/* Tool stats */}
          <div>
            <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)', marginBottom: '10px', letterSpacing: '0.05em' }}>FERRAMENTAS — ÚLTIMOS 7 DIAS</p>
            {tools.length === 0 ? (
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', padding: '12px' }}>Nenhuma chamada registrada ainda.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '220px', overflowY: 'auto' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto auto auto', gap: '8px', padding: '4px 8px', fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
                  <span>FERRAMENTA</span><span style={{ textAlign: 'right' }}>CHAMADAS</span><span style={{ textAlign: 'right' }}>AVG</span><span style={{ textAlign: 'right' }}>SUCESSO</span>
                </div>
                {tools.map(t => (
                  <div key={t.tool} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto auto', gap: '8px', padding: '6px 8px', background: 'var(--surface-hover)', borderRadius: '6px', alignItems: 'center' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-primary)', fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.tool}</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'right' }}>{t.calls}×</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'right' }}>{t.avg_ms}ms</span>
                    <span style={{ fontSize: '11px', fontWeight: 600, textAlign: 'right', color: t.success_rate >= 90 ? '#4ade80' : t.success_rate >= 70 ? '#fbbf24' : '#f87171' }}>
                      {t.success_rate}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* LLM call spans (tracing.py) */}
          <div>
            <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)', marginBottom: '10px', letterSpacing: '0.05em' }}>MODELOS LLM — ÚLTIMAS 24H</p>
            {llmCalls.length === 0 ? (
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', padding: '12px' }}>Nenhuma chamada registrada ainda.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '220px', overflowY: 'auto' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto auto auto auto', gap: '8px', padding: '4px 8px', fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
                  <span>MODELO</span><span style={{ textAlign: 'right' }}>CHAMADAS</span><span style={{ textAlign: 'right' }}>AVG</span><span style={{ textAlign: 'right' }}>TPS</span><span style={{ textAlign: 'right' }}>ERRO</span>
                </div>
                {llmCalls.map(m => (
                  <div key={m.model} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto auto auto', gap: '8px', padding: '6px 8px', background: 'var(--surface-hover)', borderRadius: '6px', alignItems: 'center' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-primary)', fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {m.model}{m.fallbacks > 0 && <span style={{ color: '#fbbf24' }}> ⚠{m.fallbacks}</span>}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'right' }}>{m.calls}×</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'right' }}>{m.avg_ms}ms</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'right' }}>{m.avg_tps}</span>
                    <span style={{ fontSize: '11px', fontWeight: 600, textAlign: 'right', color: m.error_rate === 0 ? '#4ade80' : m.error_rate <= 20 ? '#fbbf24' : '#f87171' }}>
                      {m.error_rate}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Knowledge graph */}
          {kg && (kg.entities > 0 || kg.relations > 0) && (
            <div>
              <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)', marginBottom: '10px', letterSpacing: '0.05em' }}>GRAFO DE CONHECIMENTO</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <MetricCard label="Entidades" value={`${kg.entities}`} unit="nós" color="#a78bfa" />
                <MetricCard label="Relações" value={`${kg.relations}`} unit="triplas" color="#60a5fa" />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function MetricCard({ label, value, unit, color }: { label: string; value: string; unit: string; color: string }) {
  return (
    <div style={{
      background: 'var(--surface-hover)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      padding: '12px',
      textAlign: 'center',
    }}>
      <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px' }}>{label}</p>
      <p style={{ fontSize: '22px', fontWeight: 700, color, lineHeight: 1, fontFamily: 'monospace' }}>{value}</p>
      <p style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>{unit}</p>
    </div>
  )
}

type RagDoc = { file: string; chunks: number; pages?: number; path?: string }
type IndexResult = { status: string; file: string; chunks?: number; error?: string }

function RagModal({ onClose }: { onClose: () => void }) {
  const [docs, setDocs] = useState<RagDoc[]>([])
  const [folderPath, setFolderPath] = useState('')
  const [recursive, setRecursive] = useState(false)
  const [indexing, setIndexing] = useState(false)
  const [results, setResults] = useState<IndexResult[]>([])
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadDocs = useCallback(async () => {
    try { const d = await fetchRagDocs(); setDocs(d.docs) } catch {}
  }, [])

  useEffect(() => { loadDocs() }, [loadDocs])

  const handleIndexFolder = async () => {
    if (!folderPath.trim()) return
    setIndexing(true)
    setResults([])
    try {
      const r = await ragIndexFolder(folderPath.trim(), recursive)
      setResults(r.results)
      await loadDocs()
    } catch (e: unknown) {
      setResults([{ status: 'error', file: folderPath, error: String(e) }])
    } finally {
      setIndexing(false)
    }
  }

  const handleDelete = async (fname: string) => {
    try { await ragDeleteDoc(fname); await loadDocs() } catch {}
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const files = Array.from(e.dataTransfer.files)
    if (!files.length) return
    setUploading(true)
    const r: IndexResult[] = []
    for (const f of files) {
      try {
        const res = await uploadFile(f)
        r.push({ status: 'indexed', file: res.name, chunks: (res.rag as { chunks?: number } | undefined)?.chunks })
      } catch {
        r.push({ status: 'error', file: f.name, error: 'Falha no upload' })
      }
    }
    setResults(r)
    setUploading(false)
    await loadDocs()
  }

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-lg)',
          width: '100%',
          maxWidth: '520px',
          maxHeight: '80vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
        }}
        className="anim-fade-up"
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={15} style={{ color: 'var(--accent)' }} />
            <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>Indexação de Documentos (RAG)</span>
          </div>
          <button onClick={onClose} style={{ color: 'var(--text-muted)', background: 'none', fontSize: '18px', cursor: 'pointer' }}>×</button>
        </div>

        <div style={{ overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

          {/* Drag & Drop zone */}
          <div>
            <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)', marginBottom: '8px' }}>ARRASTAR ARQUIVOS</p>
            <input ref={fileInputRef} type="file" multiple accept=".pdf,.txt,.md,.docx" style={{ display: 'none' }} onChange={async e => {
              const files = Array.from(e.target.files ?? [])
              if (!files.length) return
              setUploading(true)
              const r: IndexResult[] = []
              for (const f of files) {
                try { const res = await uploadFile(f); r.push({ status: 'indexed', file: res.name }) }
                catch { r.push({ status: 'error', file: f.name, error: 'Falha' }) }
              }
              setResults(r); setUploading(false); await loadDocs()
              if (fileInputRef.current) fileInputRef.current.value = ''
            }} />
            <div
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: `2px dashed ${dragging ? 'var(--accent)' : 'var(--border-strong)'}`,
                borderRadius: 'var(--radius-sm)',
                padding: '24px',
                textAlign: 'center',
                cursor: 'pointer',
                background: dragging ? 'var(--accent-glow)' : 'var(--surface-hover)',
                transition: 'all 0.15s',
              }}
            >
              {uploading
                ? <Loader2 size={20} style={{ color: 'var(--accent)', animation: 'spin 1s linear infinite', margin: '0 auto 8px' }} />
                : <Database size={20} style={{ color: dragging ? 'var(--accent)' : 'var(--text-muted)', margin: '0 auto 8px' }} />
              }
              <p style={{ fontSize: '13px', color: dragging ? 'var(--accent)' : 'var(--text-muted)' }}>
                {uploading ? 'Indexando...' : 'Arraste PDF, TXT, MD, DOCX ou clique para selecionar'}
              </p>
            </div>
          </div>

          {/* Indexar pasta */}
          <div>
            <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)', marginBottom: '8px' }}>INDEXAR PASTA LOCAL</p>
            <div style={{ display: 'flex', gap: '8px' }}>
              <div style={{ position: 'relative', flex: 1 }}>
                <FolderOpen size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
                <input
                  value={folderPath}
                  onChange={e => setFolderPath(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleIndexFolder() }}
                  placeholder="C:\Users\User\Documents\Docs"
                  style={{ ...inputStyle, paddingLeft: '30px', width: '100%', boxSizing: 'border-box' }}
                />
              </div>
              <button
                onClick={handleIndexFolder}
                disabled={indexing || !folderPath.trim()}
                style={{
                  padding: '8px 14px',
                  background: indexing || !folderPath.trim() ? 'var(--surface-active)' : 'var(--accent)',
                  color: indexing || !folderPath.trim() ? 'var(--text-muted)' : '#fff',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '13px',
                  fontWeight: 500,
                  cursor: indexing || !folderPath.trim() ? 'not-allowed' : 'pointer',
                  flexShrink: 0,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  whiteSpace: 'nowrap',
                }}
              >
                {indexing ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <RefreshCw size={13} />}
                {indexing ? 'Indexando...' : 'Indexar'}
              </button>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '8px', cursor: 'pointer' }}>
              <input type="checkbox" checked={recursive} onChange={e => setRecursive(e.target.checked)} />
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Incluir subpastas</span>
            </label>
          </div>

          {/* Resultados da indexação */}
          {results.length > 0 && (
            <div>
              <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)', marginBottom: '8px' }}>RESULTADO</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '140px', overflowY: 'auto' }}>
                {results.map((r, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', padding: '5px 8px', background: 'var(--surface-hover)', borderRadius: '6px' }}>
                    {r.status === 'indexed' || r.status === 'already_indexed'
                      ? <CheckCircle size={13} style={{ color: '#4ade80', flexShrink: 0 }} />
                      : <XCircle size={13} style={{ color: '#f87171', flexShrink: 0 }} />}
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }}>{r.file}</span>
                    <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
                      {r.status === 'indexed' ? `${r.chunks} chunks` : r.status === 'already_indexed' ? 'já indexado' : r.error}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Documentos indexados */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)' }}>
                DOCUMENTOS INDEXADOS ({docs.length})
              </p>
              <button onClick={loadDocs} style={{ color: 'var(--text-muted)', background: 'none', cursor: 'pointer', padding: '2px' }}>
                <RefreshCw size={12} />
              </button>
            </div>
            {docs.length === 0 ? (
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center', padding: '16px' }}>
                Nenhum documento indexado ainda.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '200px', overflowY: 'auto' }}>
                {docs.map(doc => (
                  <div key={doc.file} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '7px 10px', background: 'var(--surface-hover)', borderRadius: '6px' }}>
                    <Database size={12} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: '12px', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.file}</p>
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {doc.chunks} chunks{doc.pages && doc.pages > 1 ? ` · ${doc.pages} págs` : ''}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDelete(doc.file)}
                      title="Remover do índice"
                      style={{ color: 'var(--text-muted)', background: 'none', cursor: 'pointer', padding: '3px', flexShrink: 0, borderRadius: '4px' }}
                      onMouseEnter={e => { e.currentTarget.style.color = '#f87171' }}
                      onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <p style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center' }}>
            Suportados: PDF · TXT · MD · DOCX — Diga "busque em meus documentos..." para pesquisar
          </p>
        </div>
      </div>
    </div>
  )
}

type SpecialistEntry = { key: string; label: string; model: string }

function AuditLogModal({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<'audit' | 'tracing'>('audit')
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [spans, setSpans] = useState<TraceSpan[]>([])
  const [toolFilter, setToolFilter] = useState('')
  const [limit, setLimit] = useState(100)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      if (tab === 'audit') {
        const d = await fetchAudit(limit, toolFilter.trim())
        setAudit(d.entries)
      } else {
        setSpans(await fetchTraceRecent(limit))
      }
      setError(false)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [tab, limit, toolFilter])

  useEffect(() => { load() }, [load])

  const cellStyle: React.CSSProperties = {
    padding: '6px 10px',
    fontSize: '11.5px',
    color: 'var(--text-secondary)',
    borderBottom: '1px solid var(--border)',
    maxWidth: '220px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  }
  const headStyle: React.CSSProperties = {
    padding: '6px 10px',
    fontSize: '10.5px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    textAlign: 'left',
    borderBottom: '1px solid var(--border-strong)',
    letterSpacing: '0.03em',
    position: 'sticky',
    top: 0,
    background: 'var(--surface)',
  }

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-lg)',
          width: '100%',
          maxWidth: '820px',
          maxHeight: '85vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
        }}
        className="anim-fade-up"
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ScrollText size={14} style={{ color: 'var(--accent)' }} />
            <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>Audit log / Tracing</span>
          </div>
          <button onClick={onClose} style={{ color: 'var(--text-muted)', background: 'none', fontSize: '18px', lineHeight: 1, cursor: 'pointer' }}>×</button>
        </div>

        {/* Tabs + filtros */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '12px 20px', borderBottom: '1px solid var(--border)', flexShrink: 0, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: '4px', background: 'var(--surface-hover)', borderRadius: '8px', padding: '3px' }}>
            {(['audit', 'tracing'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                style={{
                  fontSize: '12px',
                  padding: '5px 12px',
                  borderRadius: '6px',
                  background: tab === t ? 'var(--accent)' : 'transparent',
                  color: tab === t ? '#fff' : 'var(--text-muted)',
                  cursor: 'pointer',
                }}
              >
                {t === 'audit' ? 'Ferramentas' : 'LLM (tracing)'}
              </button>
            ))}
          </div>

          {tab === 'audit' && (
            <input
              value={toolFilter}
              onChange={e => setToolFilter(e.target.value)}
              placeholder="Filtrar por tool..."
              style={{ ...inputStyle, fontSize: '12px', padding: '6px 10px', width: '150px' }}
            />
          )}

          <select value={limit} onChange={e => setLimit(Number(e.target.value))} style={{ ...inputStyle, fontSize: '12px', padding: '6px 10px' }}>
            {[50, 100, 200, 500].map(n => <option key={n} value={n} style={{ background: '#1a1a1a' }}>{n}</option>)}
          </select>

          <button onClick={load} title="Atualizar" style={{ marginLeft: 'auto', color: 'var(--text-muted)', background: 'none', cursor: 'pointer', display: 'flex' }}>
            <RefreshCw size={14} style={loading ? { animation: 'spin 1s linear infinite' } : undefined} />
          </button>
        </div>

        {/* Conteúdo */}
        <div style={{ overflow: 'auto', flex: 1 }}>
          {error && (
            <p style={{ fontSize: '13px', color: '#f87171', textAlign: 'center', padding: '24px' }}>
              Erro ao carregar — backend disponível? (endpoint protegido por AUTH_PASSWORD se configurada)
            </p>
          )}

          {!error && tab === 'audit' && (
            audit.length === 0 ? (
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', padding: '24px' }}>Nenhuma entrada.</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={headStyle}>Hora</th>
                    <th style={headStyle}>Tool</th>
                    <th style={headStyle}>Input</th>
                    <th style={headStyle}>Output</th>
                    <th style={headStyle}>ms</th>
                    <th style={headStyle}>IP</th>
                  </tr>
                </thead>
                <tbody>
                  {audit.map((e, i) => (
                    <tr key={i}>
                      <td style={{ ...cellStyle, maxWidth: '110px' }}>{e.ts.replace('T', ' ')}</td>
                      <td style={{ ...cellStyle, maxWidth: '100px', fontFamily: 'monospace' }}>{e.tool}</td>
                      <td style={cellStyle} title={e.input}>{e.input}</td>
                      <td style={cellStyle} title={e.output}>{e.output}</td>
                      <td style={{ ...cellStyle, maxWidth: '60px' }}>{Math.round((e.duration ?? 0) * 1000)}</td>
                      <td style={{ ...cellStyle, maxWidth: '90px' }}>{e.ip || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}

          {!error && tab === 'tracing' && (
            spans.length === 0 ? (
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', padding: '24px' }}>Nenhum span.</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={headStyle}>Hora</th>
                    <th style={headStyle}>Model</th>
                    <th style={headStyle}>ms</th>
                    <th style={headStyle}>Tokens</th>
                    <th style={headStyle}>TPS</th>
                    <th style={headStyle}>Status</th>
                    <th style={headStyle}>Prompt</th>
                  </tr>
                </thead>
                <tbody>
                  {spans.map((s, i) => (
                    <tr key={i}>
                      <td style={{ ...cellStyle, maxWidth: '110px' }}>{s.ts.replace('T', ' ')}</td>
                      <td style={{ ...cellStyle, maxWidth: '130px', fontFamily: 'monospace' }}>{s.model}</td>
                      <td style={{ ...cellStyle, maxWidth: '60px' }}>{Math.round(s.duration_ms)}</td>
                      <td style={{ ...cellStyle, maxWidth: '80px' }}>{s.prompt_tokens}/{s.completion_tokens}</td>
                      <td style={{ ...cellStyle, maxWidth: '50px' }}>{s.tps || '—'}</td>
                      <td style={{ ...cellStyle, maxWidth: '90px', color: s.success ? '#4ade80' : '#f87171' }}>
                        {s.success ? (s.fallback_used ? 'fallback' : 'ok') : 'erro'}
                      </td>
                      <td style={cellStyle} title={s.prompt_preview || s.error}>{s.prompt_preview || s.error}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}
        </div>
      </div>
    </div>
  )
}

function PluginMarketplaceModal({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<'buscar' | 'estagiados' | 'registries' | 'autores'>('buscar')

  // -- Buscar --
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<PluginSearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')

  // -- Estagiados --
  const [staged, setStaged] = useState<StagedPlugin[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)
  const [code, setCode] = useState<Record<string, string>>({})
  const [viewed, setViewed] = useState<Record<string, boolean>>({})
  const [busy, setBusy] = useState<string | null>(null)
  const [stagedError, setStagedError] = useState('')

  const loadStaged = useCallback(async () => {
    try {
      const d = await fetchStagedPlugins()
      setStaged(d.plugins)
      setStagedError('')
    } catch {
      setStagedError('Erro ao carregar plugins estagiados — backend disponível?')
    }
  }, [])

  useEffect(() => { loadStaged() }, [loadStaged])

  const doSearch = async () => {
    setSearching(true)
    setSearchError('')
    try {
      const d = await searchPlugins(query)
      setResults(d.results)
    } catch {
      setSearchError('Erro na busca — cheque se há registries configuradas na aba Registries.')
    } finally {
      setSearching(false)
    }
  }

  const doStage = async (manifestUrl: string) => {
    setBusy(manifestUrl)
    try {
      await stagePlugin(manifestUrl)
      await loadStaged()
      setTab('estagiados')
    } catch (e) {
      setSearchError(e instanceof Error ? e.message : 'Erro ao estagiar plugin')
    } finally {
      setBusy(null)
    }
  }

  const toggleExpand = async (name: string) => {
    if (expanded === name) {
      setExpanded(null)
      return
    }
    setExpanded(name)
    if (code[name]) {
      setViewed(v => ({ ...v, [name]: true }))
      return
    }
    try {
      const d = await fetchStagedPluginCode(name)
      setCode(c => ({ ...c, [name]: d.code }))
      setViewed(v => ({ ...v, [name]: true }))
    } catch {
      setCode(c => ({ ...c, [name]: '# erro ao carregar código' }))
    }
  }

  const doApprove = async (name: string) => {
    setBusy(name)
    try {
      await approvePlugin(name)
      await loadStaged()
    } catch (e) {
      setStagedError(e instanceof Error ? e.message : 'Erro ao aprovar plugin')
    } finally {
      setBusy(null)
    }
  }

  const tabBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: '6px 12px',
    fontSize: '12.5px',
    fontWeight: 600,
    color: active ? 'var(--text-primary)' : 'var(--text-muted)',
    borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
    background: 'none',
    cursor: 'pointer',
  })

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-lg)',
          width: '100%',
          maxWidth: '760px',
          maxHeight: '80vh',
          overflow: 'hidden',
          boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
        }}
        className="anim-fade-up"
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
          <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>Plugin Marketplace</span>
          <button onClick={onClose} style={{ color: 'var(--text-muted)', background: 'none', fontSize: '18px', lineHeight: 1, cursor: 'pointer' }}>×</button>
        </div>

        <div style={{ display: 'flex', gap: '4px', padding: '8px 20px 0', borderBottom: '1px solid var(--border)' }}>
          <button style={tabBtnStyle(tab === 'buscar')} onClick={() => setTab('buscar')}>Buscar</button>
          <button style={tabBtnStyle(tab === 'estagiados')} onClick={() => setTab('estagiados')}>Estagiados</button>
          <button style={tabBtnStyle(tab === 'registries')} onClick={() => setTab('registries')}>Registries</button>
          <button style={tabBtnStyle(tab === 'autores')} onClick={() => setTab('autores')}>Autores confiáveis</button>
        </div>

        <div style={{ padding: '16px 20px', overflowY: 'auto', flex: 1 }}>
          {tab === 'buscar' && (
            <div>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                <input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') doSearch() }}
                  placeholder="Buscar plugin por nome/descrição/tag..."
                  style={{ flex: 1, padding: '8px 10px', fontSize: '13px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)' }}
                />
                <button onClick={doSearch} disabled={searching} style={{ padding: '8px 14px', fontSize: '12.5px', fontWeight: 600, borderRadius: '8px', background: 'var(--accent)', color: '#fff', cursor: 'pointer' }}>
                  {searching ? 'Buscando...' : 'Buscar'}
                </button>
              </div>
              {searchError && <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '10px' }}>{searchError}</div>}
              {results.map(r => (
                <div key={r.manifest_url} style={{ padding: '10px 12px', border: '1px solid var(--border)', borderRadius: '8px', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{r.name}</span>
                    <button
                      onClick={() => doStage(r.manifest_url)}
                      disabled={busy === r.manifest_url}
                      style={{ padding: '4px 10px', fontSize: '11.5px', fontWeight: 600, borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: 'var(--text-primary)', cursor: 'pointer' }}
                    >
                      {busy === r.manifest_url ? 'Estagiando...' : 'Estagiar'}
                    </button>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>{r.description}</div>
                  {r.author_id && <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>autor: {r.author_id}</div>}
                </div>
              ))}
              {!searching && results.length === 0 && (
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Nenhum resultado. Confira a aba Registries se nada aparecer.</div>
              )}
            </div>
          )}

          {tab === 'estagiados' && (
            <div>
              {stagedError && <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '10px' }}>{stagedError}</div>}
              {staged.length === 0 && <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Nenhum plugin estagiado ainda.</div>}
              {staged.map(p => (
                <div key={p.name} style={{ border: '1px solid var(--border)', borderRadius: '8px', marginBottom: '8px', overflow: 'hidden' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px' }}>
                    <div>
                      <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{p.name}</span>
                      <span style={{ fontSize: '11px', color: p.status === 'approved' ? '#4ade80' : 'var(--text-muted)', marginLeft: '8px' }}>{p.status}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {p.status === 'staged' && (
                        <button onClick={() => toggleExpand(p.name)} style={{ padding: '4px 10px', fontSize: '11.5px', fontWeight: 600, borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: 'var(--text-primary)', cursor: 'pointer' }}>
                          {expanded === p.name ? 'Ocultar código' : 'Ver código'}
                        </button>
                      )}
                      {p.status === 'staged' && (
                        <button
                          onClick={() => doApprove(p.name)}
                          disabled={!viewed[p.name] || busy === p.name}
                          title={!viewed[p.name] ? 'Leia o código antes de aprovar' : undefined}
                          style={{ padding: '4px 10px', fontSize: '11.5px', fontWeight: 600, borderRadius: '6px', background: viewed[p.name] ? 'var(--accent)' : 'var(--bg-secondary)', color: viewed[p.name] ? '#fff' : 'var(--text-muted)', cursor: viewed[p.name] ? 'pointer' : 'not-allowed' }}
                        >
                          {busy === p.name ? 'Aprovando...' : 'Aprovar'}
                        </button>
                      )}
                    </div>
                  </div>
                  {expanded === p.name && (
                    <div style={{ padding: '0 12px 12px' }}>
                      <CodeBlock language="python">{code[p.name] ?? '# carregando...'}</CodeBlock>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === 'registries' && <PluginRegistriesTab />}
          {tab === 'autores' && <PluginTrustedAuthorsTab />}
        </div>
      </div>
    </div>
  )
}

function PluginRegistriesTab() {
  const [registries, setRegistries] = useState<string[]>([])
  const [newUrl, setNewUrl] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const d = await fetchPluginRegistries()
      setRegistries(d.registries)
      setError('')
    } catch {
      setError('Erro ao carregar registries.')
    }
  }, [])

  useEffect(() => { load() }, [load])

  const add = async () => {
    if (!newUrl.trim()) return
    try {
      const d = await addPluginRegistry(newUrl.trim())
      setRegistries(d.registries)
      setNewUrl('')
    } catch {
      setError('Erro ao adicionar registry.')
    }
  }

  const remove = async (url: string) => {
    try {
      const d = await removePluginRegistry(url)
      setRegistries(d.registries)
    } catch {
      setError('Erro ao remover registry.')
    }
  }

  return (
    <div>
      <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: '10px' }}>
        Registries adicionadas aqui ficam só em memória — não sobrevivem a um restart do backend. Pra deixar permanente, edite <code>PLUGIN_REGISTRY_URLS</code> em <code>config.py</code>.
      </div>
      {error && <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '10px' }}>{error}</div>}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        <input
          value={newUrl}
          onChange={e => setNewUrl(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') add() }}
          placeholder="https://... ou caminho local do registry.json"
          style={{ flex: 1, padding: '8px 10px', fontSize: '13px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)' }}
        />
        <button onClick={add} style={{ padding: '8px 14px', fontSize: '12.5px', fontWeight: 600, borderRadius: '8px', background: 'var(--accent)', color: '#fff', cursor: 'pointer' }}>Adicionar</button>
      </div>
      {registries.map(url => (
        <div key={url} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: '8px', marginBottom: '6px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', wordBreak: 'break-all' }}>{url}</span>
          <button onClick={() => remove(url)} style={{ color: 'var(--text-muted)', background: 'none', cursor: 'pointer', flexShrink: 0, marginLeft: '8px' }}><Trash2 size={13} /></button>
        </div>
      ))}
    </div>
  )
}

function PluginTrustedAuthorsTab() {
  const [authors, setAuthors] = useState<TrustedAuthor[]>([])
  const [authorId, setAuthorId] = useState('')
  const [pubkey, setPubkey] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const d = await fetchTrustedAuthors()
      setAuthors(d.authors)
    } catch {
      setError('Erro ao carregar autores confiáveis.')
    }
  }, [])

  useEffect(() => { load() }, [load])

  const add = async () => {
    if (!authorId.trim() || !pubkey.trim()) return
    setError('')
    try {
      const d = await trustPluginAuthor(authorId.trim(), pubkey.trim())
      setAuthors(d.authors)
      setAuthorId('')
      setPubkey('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao confiar no autor — chave pública inválida?')
    }
  }

  const remove = async (id: string) => {
    try {
      const d = await untrustPluginAuthor(id)
      setAuthors(d.authors)
    } catch {
      setError('Erro ao remover autor confiável.')
    }
  }

  return (
    <div>
      <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: '10px' }}>
        A chave pública precisa vir de um canal que você confia (não do próprio manifest do plugin) — é o que impede um manifest malicioso de se autodeclarar confiável.
      </div>
      {error && <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '10px' }}>{error}</div>}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
        <input value={authorId} onChange={e => setAuthorId(e.target.value)} placeholder="author_id"
          style={{ flex: '1 1 120px', padding: '8px 10px', fontSize: '13px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)' }} />
        <input value={pubkey} onChange={e => setPubkey(e.target.value)} placeholder="chave pública Ed25519 (hex)"
          style={{ flex: '2 1 220px', padding: '8px 10px', fontSize: '13px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)' }} />
        <button onClick={add} style={{ padding: '8px 14px', fontSize: '12.5px', fontWeight: 600, borderRadius: '8px', background: 'var(--accent)', color: '#fff', cursor: 'pointer' }}>Confiar</button>
      </div>
      {authors.map(a => (
        <div key={a.author_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: '8px', marginBottom: '6px' }}>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{a.author_id}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', wordBreak: 'break-all' }}>{a.pubkey}</div>
          </div>
          <button onClick={() => remove(a.author_id)} style={{ color: 'var(--text-muted)', background: 'none', cursor: 'pointer', flexShrink: 0, marginLeft: '8px' }}><Trash2 size={13} /></button>
        </div>
      ))}
    </div>
  )
}

function SpecialistModelsModal({ models, onClose }: { models: string[]; onClose: () => void }) {
  const [specialists, setSpecialists] = useState<SpecialistEntry[]>([])
  const [enabled, setEnabled] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetchSpecialistModels()
      .then(d => { setSpecialists(d.specialists); setEnabled(d.enabled) })
      .catch(() => setError(true))
  }, [])

  const handleChange = async (key: string, model: string) => {
    setSaving(key)
    try {
      await setSpecialistModel(key, model)
      setSpecialists(prev => prev.map(s => s.key === key ? { ...s, model } : s))
    } catch {
      setError(true)
    } finally {
      setSaving(null)
    }
  }

  return (
    <Modal title="Modelos por Especialista" onClose={onClose}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {error && (
          <p style={{ fontSize: '12px', color: '#f87171' }}>Erro ao carregar. Backend disponível?</p>
        )}
        {!enabled && !error && (
          <p style={{ fontSize: '12px', color: '#fbbf24', background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', lineHeight: 1.5 }}>
            Desligado (SPECIALIST_MODELS_ENABLED=False em config.py) — bloqueado por hardware, troca de modelo por especialista causa thrashing de VRAM com GPU de 6GB. Todos usam o modelo principal.
          </p>
        )}
        {specialists.length === 0 && !error && (
          <div style={{ textAlign: 'center', padding: '16px' }}>
            <Loader2 size={18} style={{ color: 'var(--accent)', animation: 'spin 1s linear infinite', margin: '0 auto' }} />
          </div>
        )}
        {specialists.map(s => (
          <div key={s.key} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', minWidth: '110px', flexShrink: 0 }}>
              {s.label}
            </span>
            <select
              value={s.model}
              onChange={e => handleChange(s.key, e.target.value)}
              disabled={saving === s.key || !enabled}
              style={{
                ...inputStyle,
                fontSize: '12px',
                padding: '6px 10px',
                opacity: (saving === s.key || !enabled) ? 0.6 : 1,
              }}
            >
              {models.map(m => (
                <option key={m} value={m} style={{ background: '#1a1a1a' }}>{m}</option>
              ))}
            </select>
            {saving === s.key && (
              <Loader2 size={13} style={{ color: 'var(--accent)', animation: 'spin 1s linear infinite', flexShrink: 0 }} />
            )}
          </div>
        ))}
        <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px', lineHeight: 1.6 }}>
          Mudancas aplicadas imediatamente. Sem reiniciar.
        </p>
      </div>
    </Modal>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
      <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-muted)' }}>{label}</span>
      {children}
    </label>
  )
}

const inputStyle: React.CSSProperties = {
  padding: '8px 12px',
  background: 'var(--surface-hover)',
  border: '1px solid var(--border-strong)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text-primary)',
  fontSize: '14px',
  outline: 'none',
  width: '100%',
  fontFamily: 'inherit',
}
