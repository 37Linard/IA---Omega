import { test, expect } from '@playwright/test'

/**
 * Cobre o caminho client-side otimista: bolha do usuário e estado "running"
 * aparecem via addUserMessage()/startAssistantMessage() (useAgentWebSocket.ts)
 * ANTES de qualquer resposta real do agente chegar pelo WS. Cancela em
 * seguida de propósito — não espera resposta real, não precisa do Ollama.
 * Ver chat-full-response.spec.ts pro caminho completo (precisa Ollama).
 */
test.describe('chat — envio otimista', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await expect(page.getByPlaceholder('Mensagem para o agente...')).toBeVisible({ timeout: 30000 })
  })

  test('enviar mensagem mostra a bolha do usuário na hora', async ({ page }) => {
    const text = `teste e2e ${Date.now()}`
    await page.getByPlaceholder('Mensagem para o agente...').fill(text)
    await page.getByTitle('Enviar (Ctrl+Enter)').click()

    await expect(page.locator('.md-content-user').last()).toHaveText(text)
  })

  test('durante o envio, botão vira Cancelar e input trava', async ({ page }) => {
    const text = `teste cancelamento ${Date.now()}`
    await page.getByPlaceholder('Mensagem para o agente...').fill(text)
    await page.getByTitle('Enviar (Ctrl+Enter)').click()

    const cancelBtn = page.getByTitle('Cancelar')
    await expect(cancelBtn).toBeVisible()
    await expect(page.getByPlaceholder('Mensagem para o agente...')).toBeDisabled()

    await cancelBtn.click()
    await expect(page.getByTitle('Enviar (Ctrl+Enter)')).toBeVisible()
  })

  test('Ctrl+Enter envia a mensagem', async ({ page }) => {
    const text = `teste ctrl-enter ${Date.now()}`
    const textarea = page.getByPlaceholder('Mensagem para o agente...')
    await textarea.fill(text)
    await textarea.press('Control+Enter')

    await expect(page.locator('.md-content-user').last()).toHaveText(text)
    // limpa o estado "running" pra não vazar pro próximo teste
    await page.getByTitle('Cancelar').click()
  })
})
