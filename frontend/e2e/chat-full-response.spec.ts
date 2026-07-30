import { test, expect } from '@playwright/test'

/**
 * Caminho completo: espera resposta REAL do agente (LLM via Ollama).
 * Pula (fail-open, mesmo padrão do hooks/pre-push) se o Ollama não
 * estiver de pé — não faz sentido travar/quebrar o suite inteiro por
 * causa disso, mas também não finge sucesso silenciosamente: reporta
 * "skipped", não "passed".
 */
let ollamaUp = false

test.beforeAll(async () => {
  try {
    const r = await fetch('http://localhost:11434', { signal: AbortSignal.timeout(3000) })
    ollamaUp = r.ok
  } catch {
    ollamaUp = false
  }
})

test.describe('chat — resposta completa do agente', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!ollamaUp, 'Ollama não está rodando em localhost:11434 — rode `ollama serve` primeiro.')
    await page.goto('/')
    await expect(page.getByPlaceholder('Mensagem para o agente...')).toBeVisible({ timeout: 30000 })
  })

  test('pergunta simples recebe resposta com conteúdo real', async ({ page }) => {
    const textarea = page.getByPlaceholder('Mensagem para o agente...')
    await textarea.fill('responda só "ok" e nada mais')
    await page.getByTitle('Enviar (Ctrl+Enter)').click()

    // até 90s — modelo local pode ser lento na 1ª chamada (carrega na VRAM)
    await expect(page.getByTitle('Enviar (Ctrl+Enter)')).toBeVisible({ timeout: 90000 })

    const response = page.locator('.md-content').last()
    await expect(response).toBeVisible()
    const content = await response.textContent()
    expect(content?.trim().length).toBeGreaterThan(0)
  })

  test('resposta concluída mostra botões de ação (copiar/regenerar)', async ({ page }) => {
    const textarea = page.getByPlaceholder('Mensagem para o agente...')
    await textarea.fill('diga oi')
    await page.getByTitle('Enviar (Ctrl+Enter)').click()
    await expect(page.getByTitle('Enviar (Ctrl+Enter)')).toBeVisible({ timeout: 90000 })

    await expect(page.getByTitle('Copiar')).toBeVisible()
  })
})
