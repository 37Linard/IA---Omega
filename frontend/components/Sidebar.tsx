'use client'

import { useState, useMemo } from 'react'
import { Plus, Search, Trash2, MessageSquare, X, Bot, PenSquare, ImagePlus, BarChart3 } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { cn } from '@/lib/utils'
import type { Conversation } from '@/lib/types'
import { isToday, isYesterday, format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

function getGroup(d: Date): string {
  if (isToday(d))     return 'Hoje'
  if (isYesterday(d)) return 'Ontem'
  const diff = (Date.now() - d.getTime()) / 86400000
  if (diff < 7)  return 'Últimos 7 dias'
  if (diff < 30) return 'Últimos 30 dias'
  return format(d, 'MMMM yyyy', { locale: ptBR })
}

function groupConversations(convs: Conversation[]) {
  const order: string[] = []
  const map: Record<string, Conversation[]> = {}
  for (const c of convs) {
    const g = getGroup(new Date(c.updatedAt))
    if (!map[g]) { map[g] = []; order.push(g) }
    map[g].push(c)
  }
  return order.map(g => ({ label: g, items: map[g] }))
}

interface Props {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: Props) {
  const [search, setSearch] = useState('')
  const [genType, setGenType] = useState<'image' | 'chart' | null>(null)
  const [genText, setGenText] = useState('')
  const store = useChatStore()

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    if (!q) return store.conversations
    return store.conversations.filter(c =>
      c.title.toLowerCase().includes(q) ||
      c.messages.some(m => m.content.toLowerCase().includes(q))
    )
  }, [store.conversations, search])

  const groups = useMemo(() => groupConversations(filtered), [filtered])

  const handleNew = () => {
    store.newConversation()
    onClose()
  }

  const openGenerate = (type: 'image' | 'chart') => {
    setGenType(type)
    setGenText('')
  }

  const handleGenerate = () => {
    const text = genText.trim()
    if (!text) return
    if (!store.getActive()) store.newConversation()
    const label = genType === 'image' ? `🎨 Gerar imagem: ${text.slice(0, 40)}` : `📊 Gerar gráfico: ${text.slice(0, 40)}`
    const task  = genType === 'image' ? `Gere uma imagem: ${text}` : `Gere um gráfico: ${text}`
    store.setPendingTemplateTask({ task, templateId: '', templateInputs: {}, displayLabel: label })
    setGenType(null)
    setGenText('')
    onClose()
  }

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 lg:hidden"
          style={{ background: 'rgba(0,0,0,0.5)' }}
          onClick={onClose}
        />
      )}

      <aside
        style={{ background: 'var(--sidebar-bg)', borderRight: '1px solid var(--border)' }}
        className={cn(
          'fixed left-0 top-0 h-full w-[260px] flex flex-col z-50',
          'transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]',
          'lg:relative lg:translate-x-0 lg:z-auto',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Top */}
        <div className="flex items-center justify-between px-3 pt-4 pb-2">
          <div className="flex items-center gap-2.5 px-1.5">
            <div
              style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}
              className="w-7 h-7 rounded-lg flex items-center justify-center shadow-lg"
            >
              <Bot size={14} className="text-white" />
            </div>
            <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
              Agente IA
            </span>
          </div>
          <div className="flex items-center gap-1">
            <SidebarBtn onClick={handleNew} title="Nova conversa">
              <PenSquare size={15} />
            </SidebarBtn>
            <SidebarBtn onClick={onClose} title="Fechar" className="lg:hidden">
              <X size={15} />
            </SidebarBtn>
          </div>
        </div>

        {/* Search */}
        <div className="px-3 pb-2">
          <div
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
            }}
            className="flex items-center gap-2 px-3 py-2"
          >
            <Search size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar conversas"
              style={{
                background: 'transparent',
                color: 'var(--text-primary)',
                fontSize: '13px',
                width: '100%',
                outline: 'none',
              }}
              className="placeholder:text-[#6b6b6b]"
            />
          </div>
        </div>

        {/* New chat shortcut */}
        <button
          onClick={handleNew}
          style={{
            margin: '2px 12px 8px',
            padding: '8px 12px',
            background: 'var(--accent)',
            borderRadius: 'var(--radius-sm)',
            color: '#fff',
            fontSize: '13px',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'background 0.15s',
          }}
          onMouseEnter={e => ((e.target as HTMLElement).closest('button')!.style.background = 'var(--accent-hover)')}
          onMouseLeave={e => ((e.target as HTMLElement).closest('button')!.style.background = 'var(--accent)')}
        >
          <Plus size={14} />
          Nova conversa
        </button>

        {/* Quick actions: image/chart generation */}
        <div style={{ display: 'flex', gap: '6px', margin: '0 12px 10px' }}>
          <QuickActionBtn icon={<ImagePlus size={13} />} label="Imagem" onClick={() => openGenerate('image')} />
          <QuickActionBtn icon={<BarChart3 size={13} />} label="Gráfico" onClick={() => openGenerate('chart')} />
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto px-2 pb-4">
          {groups.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <MessageSquare size={22} style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
              <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                {search ? 'Nenhum resultado' : 'Sem conversas ainda'}
              </span>
            </div>
          ) : (
            groups.map(({ label, items }) => (
              <div key={label} className="mb-3">
                <p
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    padding: '4px 8px',
                    marginBottom: '2px',
                  }}
                >
                  {label}
                </p>
                {items.map(c => (
                  <ConvItem
                    key={c.id}
                    conv={c}
                    active={c.id === store.activeId}
                    onSelect={() => { store.setActive(c.id); onClose() }}
                    onDelete={() => store.deleteConversation(c.id)}
                  />
                ))}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div
          style={{ borderTop: '1px solid var(--border)', padding: '10px 16px' }}
          className="flex items-center justify-between"
        >
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            {store.conversations.length} conversa{store.conversations.length !== 1 ? 's' : ''}
          </span>
        </div>
      </aside>

      {genType && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}
          onClick={e => { if (e.target === e.currentTarget) setGenType(null) }}
        >
          <div
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border-strong)',
              borderRadius: 'var(--radius-lg)',
              width: '100%',
              maxWidth: '420px',
              overflow: 'hidden',
              boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
            }}
            className="anim-fade-up"
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
              <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                {genType === 'image' ? <ImagePlus size={15} style={{ color: 'var(--accent)' }} /> : <BarChart3 size={15} style={{ color: 'var(--accent)' }} />}
                {genType === 'image' ? 'Gerar Imagem' : 'Gerar Gráfico'}
              </span>
              <button onClick={() => setGenType(null)} style={{ color: 'var(--text-muted)', background: 'none', fontSize: '18px', lineHeight: 1, cursor: 'pointer' }}>×</button>
            </div>
            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <textarea
                autoFocus
                value={genText}
                onChange={e => setGenText(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleGenerate() }}
                placeholder={
                  genType === 'image'
                    ? 'Descreva a imagem: um gato astronauta, arte digital...'
                    : 'Descreva o gráfico: barras com vendas Jan-Abr: 120, 150, 90, 200...'
                }
                rows={4}
                style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  padding: '10px 12px',
                  background: 'var(--surface-hover)',
                  border: '1px solid var(--border-strong)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--text-primary)',
                  fontSize: '13.5px',
                  outline: 'none',
                  resize: 'vertical',
                  fontFamily: 'inherit',
                  lineHeight: 1.5,
                }}
              />
              <button
                onClick={handleGenerate}
                disabled={!genText.trim()}
                style={{
                  padding: '10px',
                  background: genText.trim() ? 'var(--accent)' : 'var(--surface-active)',
                  color: genText.trim() ? '#fff' : 'var(--text-muted)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '14px',
                  fontWeight: 500,
                  cursor: genText.trim() ? 'pointer' : 'not-allowed',
                  transition: 'opacity 0.12s',
                }}
              >
                Gerar
              </button>
              <p style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center' }}>
                Ctrl+Enter para gerar
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function ConvItem({
  conv, active, onSelect, onDelete
}: {
  conv: Conversation
  active: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  const [hovered, setHovered] = useState(false)
  const preview = conv.messages.at(-1)?.content?.slice(0, 48) || ''

  return (
    <div
      role="button"
      onClick={onSelect}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '8px 10px',
        borderRadius: 'var(--radius-sm)',
        cursor: 'pointer',
        background: active ? 'var(--surface-active)' : hovered ? 'var(--surface-hover)' : 'transparent',
        transition: 'background 0.12s',
        marginBottom: '1px',
        position: 'relative',
      }}
    >
      <MessageSquare
        size={13}
        style={{
          flexShrink: 0,
          color: active ? '#818cf8' : 'var(--text-muted)',
          transition: 'color 0.12s',
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontSize: '13px',
            fontWeight: active ? 500 : 400,
            color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {conv.title}
        </p>
        {preview && (
          <p
            style={{
              fontSize: '11.5px',
              color: 'var(--text-muted)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              marginTop: '1px',
            }}
          >
            {preview}
          </p>
        )}
      </div>
      {hovered && (
        <button
          onClick={e => { e.stopPropagation(); onDelete() }}
          style={{
            flexShrink: 0,
            padding: '3px',
            borderRadius: '6px',
            color: 'var(--text-muted)',
            background: 'transparent',
            transition: 'color 0.12s',
          }}
          onMouseEnter={e => (e.currentTarget.style.color = '#f87171')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          title="Excluir"
        >
          <Trash2 size={12} />
        </button>
      )}
    </div>
  )
}

function QuickActionBtn({
  icon, label, onClick
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '6px',
        padding: '7px 8px',
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-sm)',
        color: 'var(--text-secondary)',
        fontSize: '12px',
        fontWeight: 500,
        transition: 'all 0.12s',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.color = 'var(--accent)'
        e.currentTarget.style.borderColor = 'rgba(99,102,241,0.35)'
        e.currentTarget.style.background = 'var(--accent-glow)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.color = 'var(--text-secondary)'
        e.currentTarget.style.borderColor = 'var(--border)'
        e.currentTarget.style.background = 'var(--surface)'
      }}
    >
      {icon}
      {label}
    </button>
  )
}

function SidebarBtn({
  onClick, title, children, className
}: {
  onClick: () => void
  title: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={className}
      style={{
        padding: '6px',
        borderRadius: '8px',
        color: 'var(--text-muted)',
        background: 'transparent',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'color 0.12s, background 0.12s',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.color = 'var(--text-primary)'
        e.currentTarget.style.background = 'var(--surface-hover)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.color = 'var(--text-muted)'
        e.currentTarget.style.background = 'transparent'
      }}
    >
      {children}
    </button>
  )
}
