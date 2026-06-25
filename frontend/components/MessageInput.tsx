'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { Send, Mic, MicOff, Paperclip, Square, Loader2, ArrowUp } from 'lucide-react'
import { transcribeAudio, uploadFile } from '@/lib/api'

interface Props {
  onSend: (text: string) => void
  onCancel: () => void
  running: boolean
  connected: boolean
}

export function MessageInput({ onSend, onCancel, running, connected }: Props) {
  const [value, setValue] = useState('')
  const [recording, setRecording] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [files, setFiles] = useState<string[]>([])
  const [focused, setFocused] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const mediaRef    = useRef<MediaRecorder | null>(null)
  const chunksRef   = useRef<Blob[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 180) + 'px'
  }, [value])

  const send = useCallback(() => {
    const text = value.trim()
    if (!text || running || !connected) return
    const final = files.length ? `${text}\n\n[Arquivo: ${files.join(', ')}]` : text
    onSend(final)
    setValue('')
    setFiles([])
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }, [value, running, connected, onSend, files])

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send() }
  }

  const toggleRecording = async () => {
    if (recording) { mediaRef.current?.stop(); return }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      mediaRef.current = mr
      chunksRef.current = []
      mr.ondataavailable = e => chunksRef.current.push(e.data)
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        setRecording(false)
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        try {
          const { text } = await transcribeAudio(blob)
          if (text) setValue(v => v + (v ? ' ' : '') + text)
        } catch {}
      }
      mr.start()
      setRecording(true)
    } catch { alert('Microfone não disponível.') }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? [])
    if (!selected.length) return
    setUploading(true)
    try {
      const results = await Promise.all(selected.map(f => uploadFile(f)))
      setFiles(p => [...p, ...results.map(r => r.name)])
    } catch { alert('Falha no upload.') }
    finally { setUploading(false); if (fileInputRef.current) fileInputRef.current.value = '' }
  }

  const canSend = value.trim().length > 0 && !running && connected

  return (
    <div style={{ padding: '12px 16px 16px' }}>
      {/* File pills */}
      {files.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
          {files.map(f => (
            <span
              key={f}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                fontSize: '12px',
                color: '#818cf8',
                background: 'var(--accent-glow)',
                border: '1px solid rgba(99,102,241,0.25)',
                borderRadius: '99px',
                padding: '3px 10px',
              }}
            >
              {f}
              <button
                onClick={() => setFiles(p => p.filter(x => x !== f))}
                style={{ color: 'inherit', background: 'none', lineHeight: 1, opacity: 0.7 }}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Input container */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: '8px',
          background: 'var(--surface)',
          border: `1px solid ${focused ? 'rgba(99,102,241,0.5)' : 'var(--border-strong)'}`,
          borderRadius: 'var(--radius-lg)',
          padding: '10px 12px',
          transition: 'border-color 0.15s',
          boxShadow: focused ? '0 0 0 3px var(--accent-glow)' : 'none',
        }}
      >
        {/* Attach */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.csv,.xlsx,.xls,.py,.js,.ts,.md,.json,.png,.jpg,.jpeg,.gif,.webp"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <IconBtn
          onClick={() => fileInputRef.current?.click()}
          title="Enviar arquivo"
          disabled={uploading}
        >
          {uploading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Paperclip size={16} />}
        </IconBtn>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKey}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={connected ? 'Mensagem para o agente...' : 'Conectando ao servidor...'}
          disabled={running || !connected}
          rows={1}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            resize: 'none',
            color: 'var(--text-primary)',
            fontSize: '15px',
            lineHeight: 1.6,
            maxHeight: '180px',
            overflowY: 'auto',
            padding: '0',
            fontFamily: 'inherit',
          }}
          className="placeholder:text-[#6b6b6b] disabled:opacity-50"
        />

        {/* Mic */}
        <IconBtn
          onClick={toggleRecording}
          title={recording ? 'Parar gravação' : 'Gravar voz'}
          active={recording}
          activeColor="#f87171"
        >
          {recording ? <MicOff size={16} /> : <Mic size={16} />}
        </IconBtn>

        {/* Send / Cancel */}
        {running ? (
          <button
            onClick={onCancel}
            title="Cancelar"
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(248,113,113,0.12)',
              border: '1px solid rgba(248,113,113,0.25)',
              color: '#f87171',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              cursor: 'pointer',
              transition: 'all 0.12s',
            }}
          >
            <Square size={13} />
          </button>
        ) : (
          <button
            onClick={send}
            disabled={!canSend}
            title="Enviar (Ctrl+Enter)"
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: canSend ? 'var(--accent)' : 'var(--surface-active)',
              color: canSend ? '#fff' : 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              cursor: canSend ? 'pointer' : 'not-allowed',
              transition: 'all 0.15s',
              boxShadow: canSend ? '0 2px 8px rgba(99,102,241,0.4)' : 'none',
            }}
          >
            <ArrowUp size={15} strokeWidth={2.5} />
          </button>
        )}
      </div>

      {/* Hint */}
      <p style={{ textAlign: 'center', fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '8px' }}>
        {connected
          ? 'Ctrl+Enter para enviar · Markdown suportado'
          : '⚡ Reconectando ao backend (localhost:8000)...'}
      </p>
    </div>
  )
}

function IconBtn({
  onClick, title, children, disabled, active, activeColor
}: {
  onClick: () => void
  title: string
  children: React.ReactNode
  disabled?: boolean
  active?: boolean
  activeColor?: string
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      disabled={disabled}
      style={{
        flexShrink: 0,
        padding: '5px',
        borderRadius: '7px',
        background: active ? `${activeColor ?? 'var(--accent)'}18` : 'transparent',
        color: active ? (activeColor ?? 'var(--accent)') : 'var(--text-muted)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'all 0.12s',
        opacity: disabled ? 0.4 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
      onMouseEnter={e => { if (!disabled && !active) { e.currentTarget.style.color = 'var(--text-secondary)'; e.currentTarget.style.background = 'var(--surface-hover)' } }}
      onMouseLeave={e => { if (!disabled && !active) { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent' } }}
    >
      {children}
    </button>
  )
}
