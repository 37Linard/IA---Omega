import { test, expect } from '@playwright/test'

/**
 * Só precisa do backend de pé (uvicorn api:app, ver iniciar_frontend.bat) —
 * NÃO precisa do Ollama. WS conecta e a UI reage independente de o agente
 * conseguir gerar resposta de verdade.
 */
test.describe('shell da aplicação', () => {
  test('carrega e mostra o estado vazio', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Como posso ajudar?' })).toBeVisible()
  })

  test('conecta no backend via WebSocket', async ({ page }) => {
    await page.goto('/')
    // placeholder muda de "Conectando..." pra "Mensagem para o agente..."
    // quando o WS abre (useAgentWebSocket.connect() -> onopen)
    await expect(page.getByPlaceholder('Mensagem para o agente...')).toBeVisible({ timeout: 30000 })
  })

  test('sugestões da tela vazia ficam clicáveis só depois de conectar', async ({ page }) => {
    await page.goto('/')
    const suggestion = page.getByRole('button', { name: /cotação do dólar/i })
    await expect(suggestion).toBeVisible()
    await expect(page.getByPlaceholder('Mensagem para o agente...')).toBeVisible({ timeout: 30000 })
    await expect(suggestion).toBeEnabled()
  })

  test('botão "Nova conversa" existe e é clicável', async ({ page }) => {
    await page.goto('/')
    const newConvBtn = page.getByTitle('Nova conversa').first()
    await expect(newConvBtn).toBeVisible()
    await newConvBtn.click()
    // continua no estado vazio (não crasha, não navega pra lugar nenhum)
    await expect(page.getByRole('heading', { name: 'Como posso ajudar?' })).toBeVisible()
  })
})
