import { API_BASE } from './utils'
import type { UserProfile } from './types'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchProfile(): Promise<UserProfile> {
  return req('/profile')
}

export async function saveProfile(data: Partial<UserProfile>): Promise<UserProfile> {
  return req('/profile', { method: 'POST', body: JSON.stringify(data) })
}

export async function fetchModels(): Promise<{ models: string[]; current: string }> {
  return req('/models')
}

export async function setModel(model: string): Promise<void> {
  return req('/model', { method: 'POST', body: JSON.stringify({ model }) })
}

export async function fetchHealth() {
  return req('/health')
}

export async function uploadFile(file: File): Promise<{ path: string; name: string; rag?: unknown }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json()
}

export async function transcribeAudio(blob: Blob): Promise<{ text: string }> {
  const form = new FormData()
  form.append('file', blob, 'recording.webm')
  const res = await fetch(`${API_BASE}/transcribe`, { method: 'POST', body: form })
  if (!res.ok) throw new Error('Transcription failed')
  return res.json()
}

export async function fetchHistory(): Promise<{ sessions: Array<{ task: string; result: string; timestamp: string }> }> {
  return req('/history')
}
