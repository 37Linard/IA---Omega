import { test, expect } from '@playwright/test'

/**
 * Mesmo pré-requisito de e2e/app-shell.spec.ts — só precisa do backend de
 * pé (uvicorn api:app na 8000), não precisa do Ollama.
 */
test.describe('header responsivo — mobile (<640px)', () => {
  test.use({ viewport: { width: 375, height: 667 } })

  test('ícones secundários ficam escondidos, colapsam no botão "mais"', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByPlaceholder('Mensagem para o agente...')).toBeVisible({ timeout: 30000 })

    // Sempre visíveis, mesmo em mobile
    await expect(page.getByTitle('Status do sistema')).toBeVisible()

    // Colapsado — não aparece direto no header em telas pequenas
    await expect(page.getByTitle('Ferramentas IA — 25 ferramentas especializadas')).toBeHidden()

    // Botão "mais" aparece só em mobile
    await expect(page.getByTitle('Mais opções')).toBeVisible()
  })

  test('menu "mais" abre e lista as ações colapsadas', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByPlaceholder('Mensagem para o agente...')).toBeVisible({ timeout: 30000 })

    await page.getByTitle('Mais opções').click()

    const menu = page.getByRole('menu', { name: 'Mais opções' })
    await expect(menu).toBeVisible()
    await expect(menu.getByRole('button', { name: 'Ferramentas IA' })).toBeVisible()
    await expect(menu.getByRole('button', { name: 'Perfil' })).toBeVisible()
    await expect(menu.getByRole('button', { name: 'Audit log / Tracing' })).toBeVisible()
  })

  test('menu "mais" fecha ao clicar fora', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByPlaceholder('Mensagem para o agente...')).toBeVisible({ timeout: 30000 })

    await page.getByTitle('Mais opções').click()
    const menu = page.getByRole('menu', { name: 'Mais opções' })
    await expect(menu).toBeVisible()

    await page.mouse.click(300, 400) // fora do menu, dentro da área de chat
    await expect(menu).toBeHidden()
  })
})

test.describe('header desktop (>=640px) — sem regressão', () => {
  test('todos os ícones continuam visíveis direto, sem colapsar', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByPlaceholder('Mensagem para o agente...')).toBeVisible({ timeout: 30000 })

    await expect(page.getByTitle('Ferramentas IA — 25 ferramentas especializadas')).toBeVisible()
    await expect(page.getByTitle('Perfil')).toBeVisible()
    await expect(page.getByTitle('Status do sistema')).toBeVisible()
    await expect(page.getByTitle('Mais opções')).toBeHidden()
  })
})
