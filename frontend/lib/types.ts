export type MessageRole = 'user' | 'assistant'

export type StepType =
  | 'thought'
  | 'action'
  | 'observation'
  | 'step'
  | 'error'
  | 'agent_status'
  | 'plan'
  | 'correction'
  | 'reflection'

export interface AgentStep {
  id: string
  type: StepType
  content: string
  agent?: string
  score?: number      // reflection score 1-5
  accepted?: boolean  // reflection accepted
}

export interface TokenUsage {
  prompt: number
  completion: number
}

export interface WorkflowNode {
  id: number | string
  specialist: string
  label: string
  subtask: string
  status: 'pending' | 'running' | 'done' | 'error'
  result?: string
}

export interface WorkflowPlan {
  task: string
  nodes: WorkflowNode[]
  aggregateStatus?: 'running' | 'done'
  aggregateResult?: string
}

export interface Message {
  id: string
  role: MessageRole
  content: string
  steps: AgentStep[]
  workflow?: WorkflowPlan
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
  | { type: 'correction'; content: string }
  | { type: 'reflection'; content: string; score: number; accepted: boolean }
  | { type: 'reset_content'; content: string }
  | { type: 'token_usage'; prompt: number; completion: number }
  | { type: 'agent_status'; id?: number | string; agent: string; status: 'running' | 'done' | 'error'; subtask?: string; result?: string }
  | { type: 'workflow_plan'; task: string; nodes: { id: number; specialist: string; label: string; subtask: string }[] }
  | { type: 'hitl_request'; id: string; action: string; input: unknown; message: string }
