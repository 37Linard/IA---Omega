export type MessageRole = 'user' | 'assistant'

export type StepType =
  | 'thought'
  | 'action'
  | 'observation'
  | 'step'
  | 'error'
  | 'agent_status'
  | 'plan'

export interface AgentStep {
  id: string
  type: StepType
  content: string
  agent?: string
}

export interface TokenUsage {
  prompt: number
  completion: number
}

export interface Message {
  id: string
  role: MessageRole
  content: string
  steps: AgentStep[]
  isStreaming: boolean
  streamingThought: string
  tokenUsage?: TokenUsage
  timestamp: Date
  error?: string
  feedback?: 'up' | 'down'
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
}

export interface UserProfile {
  name: string
  tech_level: 'iniciante' | 'intermediário' | 'avançado' | 'especialista'
  tone: 'informal' | 'neutro' | 'formal' | 'técnico'
  language: string
  interactions: number
}

export type WsMessage =
  | { type: 'step'; content: string }
  | { type: 'thought'; content: string }
  | { type: 'action'; content: string }
  | { type: 'observation'; content: string }
  | { type: 'token_start'; content: string }
  | { type: 'token'; content: string }
  | { type: 'token_end'; content: string }
  | { type: 'final_stream_start'; content: string }
  | { type: 'final_token'; content: string }
  | { type: 'final_stream_end'; content: string }
  | { type: 'final'; content: string }
  | { type: 'done'; content: string }
  | { type: 'error'; content: string }
  | { type: 'token_usage'; prompt: number; completion: number }
  | { type: 'agent_status'; agent: string; status: 'running' | 'done'; subtask?: string; result?: string }
