'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { getTemplate } from '@/lib/templates'
import { useChatStore } from '@/store/chatStore'
import type { TemplateCampo } from '@/lib/templates'

function CampoInput({ campo, value, onChange }: {
  campo: TemplateCampo
  value: string
  onChange: (v: string) => void
}) {
  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px 14px',
    background: '#1a1a1a',
    border: '1px solid #2a2a2a',
    borderRadius: 8,
    color: '#e5e5e5',
    fontSize: 14,
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.15s',
    fontFamily: 'inherit',
  }

  const onFocus = (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    (e.target.style.borderColor = '#6366f1')
  const onBlur = (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    (e.target.style.borderColor = '#2a2a2a')

  if (campo.tipo === 'select') {
    return (
      <select value={value} onChange={e => onChange(e.target.value)} onFocus={onFocus} onBlur={onBlur}
        style={{ ...inputStyle, cursor: 'pointer' }}>
        <option value="">Selecione...</option>
        {campo.opcoes?.map(op => <option key={op} value={op}>{op}</option>)}
      </select>
    )
  }

  if (campo.tipo === 'textarea') {
    return (
      <textarea value={value} onChange={e => onChange(e.target.value)} onFocus={onFocus} onBlur={onBlur}
        placeholder={campo.placeholder} rows={4}
        style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.5 }} />
    )
  }

  return (
    <input type="text" value={value} onChange={e => onChange(e.target.value)} onFocus={onFocus} onBlur={onBlur}
      placeholder={campo.placeholder} style={inputStyle} />
  )
}

const OPCIONAIS = new Set([
  'duvidas_comuns', 'referencias', 'concorrentes_seo',
  'melhores_clientes', 'ajustes', 'objecoes', 'problemas',
])

export function FerramentaForm({ id }: { id: string }) {
  const router = useRouter()
  const template = getTemplate(id)
  const setPendingTemplateTask = useChatStore(s => s.setPendingTemplateTask)
  const newConversation = useChatStore(s => s.newConversation)

  const [valores, setValores] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {}
    template?.campos.forEach(c => { init[c.nome] = '' })
    return init
  })
  const [erro, setErro] = useState<string | null>(null)

  if (!template) {
    return (
      <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#e5e5e5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>❌</div>
          <p>Ferramenta não encontrada.</p>
          <button onClick={() => router.push('/ferramentas')}
            style={{ marginTop: 12, padding: '8px 20px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
            Voltar
          </button>
        </div>
      </div>
    )
  }

  const setValor = (nome: string, valor: string) => setValores(v => ({ ...v, [nome]: valor }))

  const obrigatorios = template.campos.filter(c => !OPCIONAIS.has(c.nome))
  const preenchidos  = obrigatorios.filter(c => valores[c.nome]?.trim())
  const progresso    = obrigatorios.length > 0 ? Math.round((preenchidos.length / obrigatorios.length) * 100) : 100

  const handleSubmit = () => {
    const faltando = obrigatorios.filter(c => !valores[c.nome]?.trim())
    if (faltando.length > 0) {
      setErro(`Preencha: ${faltando.map(c => c.label).join(', ')}`)
      return
    }
    setErro(null)

    const primeiros = Object.values(valores).filter(v => v.trim()).slice(0, 2).map(v => v.trim().slice(0, 30))
    const displayLabel = `${template.icone} ${template.nome}${primeiros.length ? ' — ' + primeiros.join(' · ') : ''}`

    newConversation()
    setPendingTemplateTask({
      task: `Executar ${template.nome}`,
      templateId: template.id,
      templateInputs: valores,
      displayLabel,
    })
    router.push('/')
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#e5e5e5' }}>
      {/* Header */}
      <div style={{
        borderBottom: '1px solid #1f1f1f',
        padding: '20px 32px',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        background: '#111111',
        position: 'sticky',
        top: 0,
        zIndex: 10,
      }}>
        <button onClick={() => router.push('/ferramentas')}
          style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer', fontSize: 20, padding: '4px 8px', borderRadius: 6 }}
          onMouseEnter={e => (e.currentTarget.style.color = '#e5e5e5')}
          onMouseLeave={e => (e.currentTarget.style.color = '#888')}>
          ←
        </button>
        <span style={{ fontSize: 28 }}>{template.icone}</span>
        <div style={{ flex: 1 }}>
          <h1 style={{ margin: 0, fontSize: 19, fontWeight: 600, color: '#f0f0f0' }}>{template.nome}</h1>
          <p style={{ margin: 0, fontSize: 13, color: '#666', marginTop: 2 }}>{template.descricao}</p>
        </div>
        <div style={{ textAlign: 'right', minWidth: 80 }}>
          <div style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>{progresso}% preenchido</div>
          <div style={{ height: 4, background: '#1f1f1f', borderRadius: 2, width: 80 }}>
            <div style={{ height: 4, background: '#6366f1', borderRadius: 2, width: `${progresso}%`, transition: 'width 0.3s' }} />
          </div>
        </div>
      </div>

      {/* Form */}
      <div style={{ padding: '32px', maxWidth: 680, margin: '0 auto' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {template.campos.map(campo => (
            <div key={campo.nome}>
              <label style={{ display: 'block', fontSize: 14, fontWeight: 500, color: '#ccc', marginBottom: 8 }}>
                {campo.label}
                {OPCIONAIS.has(campo.nome) && (
                  <span style={{ color: '#555', fontWeight: 400, marginLeft: 6 }}>(opcional)</span>
                )}
              </label>
              <CampoInput campo={campo} value={valores[campo.nome] ?? ''} onChange={v => setValor(campo.nome, v)} />
            </div>
          ))}
        </div>

        {erro && (
          <div style={{
            marginTop: 20, padding: '12px 16px',
            background: '#1f0a0a', border: '1px solid #450a0a',
            borderRadius: 8, color: '#fca5a5', fontSize: 13,
          }}>
            {erro}
          </div>
        )}

        <div style={{ marginTop: 32, display: 'flex', gap: 12 }}>
          <button onClick={() => router.push('/ferramentas')}
            style={{ padding: '12px 24px', background: '#1f1f1f', border: '1px solid #2a2a2a', borderRadius: 8, color: '#888', cursor: 'pointer', fontSize: 14 }}
            onMouseEnter={e => { e.currentTarget.style.background = '#2a2a2a'; e.currentTarget.style.color = '#ccc' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#1f1f1f'; e.currentTarget.style.color = '#888' }}>
            Cancelar
          </button>
          <button onClick={handleSubmit}
            style={{ flex: 1, padding: '12px 24px', background: '#6366f1', border: 'none', borderRadius: 8, color: '#fff', cursor: 'pointer', fontSize: 14, fontWeight: 600 }}
            onMouseEnter={e => (e.currentTarget.style.background = '#5254cc')}
            onMouseLeave={e => (e.currentTarget.style.background = '#6366f1')}>
            Gerar com IA →
          </button>
        </div>
      </div>
    </div>
  )
}
