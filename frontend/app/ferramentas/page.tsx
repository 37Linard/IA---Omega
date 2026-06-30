'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { TEMPLATES, CATEGORIAS } from '@/lib/templates'

const CATEGORIA_CORES: Record<string, string> = {
  'Conteúdo':   '#6366f1',
  'Vendas':     '#10b981',
  'Marca':      '#f59e0b',
  'Atendimento':'#3b82f6',
  'Documentos': '#8b5cf6',
  'Educação':   '#ec4899',
  'Gestão':     '#64748b',
}

export default function FerramentasPage() {
  const router = useRouter()
  const [categoriaAtiva, setCategoriaAtiva] = useState<string>('Todas')
  const [busca, setBusca] = useState('')

  const ferramentasFiltradas = TEMPLATES.filter(t => {
    const matchCategoria = categoriaAtiva === 'Todas' || t.categoria === categoriaAtiva
    const matchBusca = busca === '' || t.nome.toLowerCase().includes(busca.toLowerCase()) || t.descricao.toLowerCase().includes(busca.toLowerCase())
    return matchCategoria && matchBusca
  })

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0a0a0a',
      color: '#e5e5e5',
    }}>
      {/* Header */}
      <div style={{
        borderBottom: '1px solid #1f1f1f',
        padding: '20px 32px',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        background: '#111111',
      }}>
        <button
          onClick={() => router.push('/')}
          style={{
            background: 'none',
            border: 'none',
            color: '#888',
            cursor: 'pointer',
            fontSize: 20,
            lineHeight: 1,
            padding: '4px 8px',
            borderRadius: 6,
            transition: 'color 0.15s',
          }}
          onMouseEnter={e => (e.currentTarget.style.color = '#e5e5e5')}
          onMouseLeave={e => (e.currentTarget.style.color = '#888')}
        >
          ←
        </button>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 600, color: '#f0f0f0' }}>
            Ferramentas IA
          </h1>
          <p style={{ margin: 0, fontSize: 13, color: '#666', marginTop: 2 }}>
            25 ferramentas especializadas — selecione, preencha e gere
          </p>
        </div>
      </div>

      <div style={{ padding: '24px 32px', maxWidth: 1200, margin: '0 auto' }}>
        {/* Busca */}
        <input
          type="text"
          placeholder="Buscar ferramenta..."
          value={busca}
          onChange={e => setBusca(e.target.value)}
          style={{
            width: '100%',
            padding: '10px 16px',
            background: '#1a1a1a',
            border: '1px solid #2a2a2a',
            borderRadius: 8,
            color: '#e5e5e5',
            fontSize: 14,
            outline: 'none',
            boxSizing: 'border-box',
            marginBottom: 20,
            transition: 'border-color 0.15s',
          }}
          onFocus={e => (e.target.style.borderColor = '#6366f1')}
          onBlur={e => (e.target.style.borderColor = '#2a2a2a')}
        />

        {/* Filtros de categoria */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28 }}>
          {['Todas', ...CATEGORIAS].map(cat => (
            <button
              key={cat}
              onClick={() => setCategoriaAtiva(cat)}
              style={{
                padding: '6px 14px',
                borderRadius: 20,
                border: 'none',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 500,
                background: categoriaAtiva === cat ? '#6366f1' : '#1f1f1f',
                color: categoriaAtiva === cat ? '#fff' : '#888',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => {
                if (categoriaAtiva !== cat) {
                  e.currentTarget.style.background = '#2a2a2a'
                  e.currentTarget.style.color = '#ccc'
                }
              }}
              onMouseLeave={e => {
                if (categoriaAtiva !== cat) {
                  e.currentTarget.style.background = '#1f1f1f'
                  e.currentTarget.style.color = '#888'
                }
              }}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Contagem */}
        <p style={{ fontSize: 13, color: '#555', marginBottom: 20 }}>
          {ferramentasFiltradas.length} ferramenta{ferramentasFiltradas.length !== 1 ? 's' : ''}
        </p>

        {/* Grid de cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 16,
        }}>
          {ferramentasFiltradas.map(template => {
            const cor = CATEGORIA_CORES[template.categoria] ?? '#6366f1'
            return (
              <button
                key={template.id}
                onClick={() => router.push(`/ferramentas/${template.id}`)}
                style={{
                  background: '#141414',
                  border: '1px solid #1f1f1f',
                  borderRadius: 12,
                  padding: '20px',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.15s',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = cor
                  e.currentTarget.style.background = '#1a1a1a'
                  e.currentTarget.style.transform = 'translateY(-1px)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = '#1f1f1f'
                  e.currentTarget.style.background = '#141414'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                {/* Ícone + categoria */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <span style={{ fontSize: 28 }}>{template.icone}</span>
                  <span style={{
                    fontSize: 11,
                    padding: '3px 8px',
                    borderRadius: 10,
                    background: cor + '22',
                    color: cor,
                    fontWeight: 500,
                  }}>
                    {template.categoria}
                  </span>
                </div>

                {/* Nome */}
                <div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: '#f0f0f0', lineHeight: 1.3 }}>
                    {template.nome}
                  </div>
                  <div style={{ fontSize: 13, color: '#666', marginTop: 4, lineHeight: 1.4 }}>
                    {template.descricao}
                  </div>
                </div>

                {/* Campos count */}
                <div style={{ fontSize: 12, color: '#444', marginTop: 'auto' }}>
                  {template.campos.length} campo{template.campos.length !== 1 ? 's' : ''} para preencher
                </div>
              </button>
            )
          })}
        </div>

        {ferramentasFiltradas.length === 0 && (
          <div style={{ textAlign: 'center', color: '#444', padding: '48px 0', fontSize: 14 }}>
            Nenhuma ferramenta encontrada para "{busca}"
          </div>
        )}
      </div>
    </div>
  )
}
