'use client'

import { useState, useEffect } from 'react'
import { Menu, Sun, Moon, User, Heart, Cpu, ChevronDown } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { fetchModels, setModel, fetchProfile, saveProfile } from '@/lib/api'
import type { UserProfile } from '@/lib/types'

interface Props { onToggleSidebar: () => void }

export function Header({ onToggleSidebar }: Props) {
  const { theme, toggleTheme, getActive } = useChatStore()
  const conv = getActive()
  const [models, setModels] = useState<string[]>([])
  const [currentModel, setCurrentModel] = useState('')
  const [profileOpen, setProfileOpen] = useState(false)
  const [healthOpen, setHealthOpen] = useState(false)
  const [profile, setProfile] = useState<UserProfile | null>(null)

  useEffect(() => {
    fetchModels().then(d => { setModels(d.models); setCurrentModel(d.current) }).catch(() => {})
    fetchProfile().then(setProfile).catch(() => {})
  }, [])

  const changeModel = async (m: string) => {
    setCurrentModel(m)
    try { await setModel(m) } catch {}
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

          <HeaderBtn onClick={() => setProfileOpen(true)} title="Perfil">
            <User size={15} />
          </HeaderBtn>

          <HeaderBtn onClick={() => setHealthOpen(true)} title="Status do sistema">
            <Heart size={15} />
          </HeaderBtn>

          <HeaderBtn onClick={toggleTheme} title={theme === 'dark' ? 'Tema claro' : 'Tema escuro'}>
            {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
          </HeaderBtn>
        </div>
      </header>

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
          <select value={form.tech_level} onChange={e => setForm(f => ({ ...f, tech_level: e.target.value as UserProfile['tech_level'] }))} style={inputStyle}>
            {(['iniciante', 'intermediário', 'avançado', 'especialista'] as const).map(v => (
              <option key={v} value={v} style={{ background: '#2a2a2a' }}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>
            ))}
          </select>
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

function HealthModal({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(r => r.json())
      .then(setData)
      .catch(() => setData({ error: 'Servidor indisponível' }))
  }, [])

  return (
    <Modal title="❤️ Status do Sistema" onClose={onClose}>
      {!data ? (
        <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Carregando...</p>
      ) : (
        <pre style={{ fontSize: '12px', fontFamily: 'monospace', whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
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
