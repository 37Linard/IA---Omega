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

export async function fetchMetrics(): Promise<{
  inference: { tps: number; ttft_ms: number; context_pct: number; prompt_tokens: number; completion_tokens: number }
  tools: Array<{ tool: string; calls: number; errors: number; success_rate: number; avg_ms: number }>
  vram: { used_mb: number; total_mb: number; free_mb: number; pct: number }
}> {
  return req('/metrics')
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

export async function fetchRagDocs(): Promise<{ docs: Array<{ file: string; chunks: number; pages?: number; path?: string }> }> {
  return req('/rag/docs')
}

export async function ragIndexFolder(path: string, recursive: boolean): Promise<{ results: Array<{ status: string; file: string; chunks?: number; error?: string }>; total: number }> {
  return req('/rag/index-folder', { method: 'POST', body: JSON.stringify({ path, recursive }) })
}

export async function ragDeleteDoc(fname: string): Promise<void> {
  await fetch(`${API_BASE}/rag/docs/${encodeURIComponent(fname)}`, { method: 'DELETE' })
}

export async function fetchSandboxStatus(): Promise<{
  mode: 'docker' | 'local'
  docker: boolean
  image: string | null
  custom?: boolean
  warning: string | null
}> {
  return req('/sandbox/status')
}

export async function fetchSpecialistModels(): Promise<{
  specialists: Array<{ key: string; label: string; model: string }>
}> {
  return req('/specialist-models')
}

export async function setSpecialistModel(specialist: string, model: string): Promise<void> {
  return req('/specialist-models', {
    method: 'POST',
    body: JSON.stringify({ specialist, model }),
  })
}
