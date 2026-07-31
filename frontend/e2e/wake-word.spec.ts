import { test, expect } from '@playwright/test'

/**
 * Só o toggle de UI + gravação real (chunk gravado, RMS calculado) — não
 * dá pra testar o disparo de /transcribe de ponta a ponta aqui: o
 * dispositivo de mic fake do Chromium (--use-fake-device-for-media-stream)
 * gera um tom de amplitude baixa (RMS medido ao vivo: ~0.005), abaixo do
 * SILENCE_RMS_THRESHOLD (0.015) — o VAD filtra como silêncio corretamente,
 * então nunca chega a mandar chunk pro backend. Validado manualmente que o
 * pipeline completo (getUserMedia -> AnalyserNode -> MediaRecorder -> RMS)
 * roda sem erro; só falta um mic real (ou fala de verdade) pra passar do
 * gate de VAD.
 */
test('modo de voz contínuo liga/desliga', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByPlaceholder('Mensagem para o agente...')).toBeVisible({ timeout: 30000 })

  const wakeBtn = page.getByTitle(/Ligar modo de voz contínuo/)
  const micBtn = page.getByTitle('Gravar voz')
  await expect(wakeBtn).toBeVisible()
  await expect(micBtn).toBeEnabled()

  await wakeBtn.click()
  await expect(page.getByText('Modo contínuo ligado')).toBeVisible({ timeout: 5000 })
  await expect(micBtn).toBeDisabled() // push-to-talk trava enquanto o modo contínuo usa o mic

  await page.getByTitle(/Modo contínuo ligado/).click()
  await expect(page.getByText('Ctrl+Enter para enviar')).toBeVisible({ timeout: 5000 })
  await expect(micBtn).toBeEnabled()
})
