import type { AgentStep } from './types'

export interface Source {
  title: string
  url: string
}

export interface ParsedAction {
  tool: string
  input: Record<string, unknown>
}

/** Extrai tool + input de um step de acao tipo `web_search({"query": "..."})`. */
export function parseActionCall(content: string): ParsedAction | null {
  const m = content.match(/^(\w+)\(([\s\S]*)\)$/)
  if (!m) return null
  try {
    const input = JSON.parse(m[2])
    return { tool: m[1], input }
  } catch {
    return null
  }
}

/** Extrai {title, url} dos resultados do web_search_tool (formato "[N] Titulo\n    URL: ..."). */
export function parseSearchResults(observation: string): Source[] {
  const out: Source[] = []
  const re = /\[\d+\]\s+([^\n]+)\n\s*URL:\s*(\S+)/g
  let m: RegExpExecArray | null
  while ((m = re.exec(observation))) {
    const title = m[1].trim()
    const url = m[2].trim()
    if (!title || !/^https?:\/\//.test(url)) continue
    out.push({ title, url })
  }
  return out
}

export function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

/** Numero de resultados de busca retornados pela observacao que segue uma acao web_search. */
export function countSearchResults(observation: string): number {
  return parseSearchResults(observation).length
}

/** Junta todas as fontes (web_search + fetch_page) encontradas ao longo dos steps de uma mensagem, sem duplicar URL. */
export function extractSources(steps: AgentStep[]): Source[] {
  const byUrl = new Map<string, Source>()

  for (let i = 0; i < steps.length; i++) {
    const step = steps[i]
    if (step.type !== 'action') continue
    const parsed = parseActionCall(step.content)
    if (!parsed) continue

    if (parsed.tool === 'web_search') {
      const obs = steps[i + 1]
      if (obs?.type === 'observation') {
        for (const src of parseSearchResults(obs.content)) {
          if (!byUrl.has(src.url)) byUrl.set(src.url, src)
        }
      }
    } else if (parsed.tool === 'fetch_page') {
      const url = typeof parsed.input.url === 'string' ? parsed.input.url : null
      if (url && !byUrl.has(url)) {
        byUrl.set(url, { title: hostnameOf(url), url })
      }
    }
  }

  return Array.from(byUrl.values())
}
