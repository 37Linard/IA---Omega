import { defineConfig, devices } from '@playwright/test'

/**
 * Alvo é sempre localhost:8000 (FastAPI serve o build estático + /ws + /api,
 * um único host:porta), NUNCA "next dev" na 3000 — WS_URL/API_BASE no
 * frontend são relativos ao host atual (lib/utils.ts), sem proxy configurado
 * (next.config.ts usa output:"export", desliga rewrites). "npm run dev" na
 * 3000 conecta em ws://localhost:3000/ws, que não existe — sempre vai
 * mostrar "Conectando..." parado, nunca abre WS de verdade.
 *
 * Pré-requisito (não é auto-iniciado por este config, mesmo padrão do
 * eval_harness.py — precondição documentada, não escondida):
 *   .\iniciar_frontend.bat   (builda o frontend + sobe uvicorn na 8000)
 * Specs que exigem resposta real do agente também precisam do Ollama de pé.
 */
export default defineConfig({
  testDir: './e2e',
  // 1ª conexão WS demora ~13-15s de verdade (create_agent() carrega ~30
  // tools no backend, achado testando) — timeout default de 30s do
  // Playwright colidia com o próprio expect({timeout:30000}) de conectar.
  timeout: 60000,
  fullyParallel: false, // WS de sessão única por navegador — paralelo real pede sessões isoladas, não vale a complexidade ainda
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [['html', { outputFolder: 'playwright-report', open: 'never' }], ['list']],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10000,
    navigationTimeout: 30000,
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        permissions: ['microphone'],
        // dispositivo de áudio/vídeo fake do Chromium -- specs de voz (modo
        // contínuo/wake word, push-to-talk) não dependem de mic real nem de
        // permissão manual
        launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] },
      },
    },
  ],
})
