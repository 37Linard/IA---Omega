import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const API_BASE = ''
export const WS_URL = typeof window !== 'undefined'
  ? `ws://${window.location.host}/ws`
  : 'ws://localhost:8000/ws'

export function generateId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

export function extractTitle(content: string): string {
  const clean = content.replace(/[#*`]/g, '').trim()
  return clean.length > 60 ? clean.slice(0, 57) + '...' : clean || 'Nova conversa'
}
