'use client'

import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism'
import { Copy, Check } from 'lucide-react'

interface Props {
  language?: string
  children: string
}

export function CodeBlock({ language = 'text', children }: Props) {
  const [copied, setCopied] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(children).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const lines = children.split('\n').length

  return (
    <div
      style={{
        borderRadius: '10px',
        overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.08)',
        margin: '10px 0',
        background: '#1e1e1e',
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 14px',
          background: '#161616',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <span style={{ fontSize: '11.5px', color: '#6b6b6b', fontFamily: 'monospace', fontWeight: 500 }}>
          {language}
        </span>
        <button
          onClick={copy}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            fontSize: '11.5px',
            padding: '3px 8px',
            borderRadius: '5px',
            background: copied ? 'rgba(74,222,128,0.12)' : 'transparent',
            color: copied ? '#4ade80' : '#6b6b6b',
            cursor: 'pointer',
            transition: 'all 0.12s',
          }}
          onMouseEnter={e => { if (!copied) { e.currentTarget.style.color = '#ececec'; e.currentTarget.style.background = 'rgba(255,255,255,0.07)' } }}
          onMouseLeave={e => { if (!copied) { e.currentTarget.style.color = '#6b6b6b'; e.currentTarget.style.background = 'transparent' } }}
        >
          {copied ? <Check size={11} /> : <Copy size={11} />}
          {copied ? 'Copiado!' : 'Copiar'}
        </button>
      </div>

      {/* Code */}
      <SyntaxHighlighter
        language={language}
        style={vscDarkPlus}
        showLineNumbers={lines > 6}
        lineNumberStyle={{ color: '#3d3d3d', minWidth: '2.2em', paddingRight: '12px', fontSize: '12px' }}
        customStyle={{
          margin: 0,
          borderRadius: 0,
          fontSize: '13px',
          padding: '14px 16px',
          background: '#1e1e1e',
          lineHeight: 1.6,
        }}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  )
}
