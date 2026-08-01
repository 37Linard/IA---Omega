# Frontend responsivo mobile — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir 2 problemas reais de responsividade mobile no frontend Next.js: altura de viewport (`100vh` não acompanha barra de endereço do navegador móvel) e header com 9 ícones que não cabem em telas estreitas.

**Architecture:** Nenhuma nova — CSS puro (`.app-shell` com fallback `100dvh`/`100vh`) pro primeiro problema; pro segundo, os 8 ícones menos usados do header colapsam num menu dropdown (`MoreMenu`, componente novo dentro de `Header.tsx`, mesmo padrão dos modais já existentes no arquivo) abaixo do breakpoint Tailwind `sm` (640px). Health e tema ficam sempre visíveis.

**Tech Stack:** Next.js 16.2.9 (App Router, Turbopack), React 19, TypeScript, Tailwind v4, lucide-react (ícones), Playwright (E2E, já configurado contra `localhost:8000`).

## Global Constraints

- Nenhuma mudança visual em desktop (>640px) — todos os 9 ícones continuam em linha, idênticos a hoje.
- Sem biblioteca nova — reusa `HeaderBtn`/padrão de modal já existentes em `Header.tsx`.
- Sem redesenho de cores/tipografia/espaçamento, sem barra de navegação inferior, sem mudança em `Sidebar.tsx`/`MessageInput.tsx` (já adequados pra mobile — ver spec).
- Spec completa: `docs/superpowers/specs/2026-08-01-frontend-mobile-responsivo-design.md`.
- Projeto usa Next.js 16 com possíveis mudanças em relação ao treino do modelo (`frontend/AGENTS.md`) — nenhuma API nova do Next é usada neste plano (só CSS, React state, Tailwind, Playwright já em uso), então não é necessário consultar `node_modules/next/dist/docs/`.
- Backend precisa estar de pé em `localhost:8000` (`iniciar_frontend.bat`) pros testes E2E rodarem — Ollama não é necessário pros testes deste plano (não dependem de resposta real do agente).

---

### Task 1: Altura de viewport mobile (`100dvh` com fallback)

**Files:**
- Modify: `frontend/app/globals.css` (adiciona regra `.app-shell`)
- Modify: `frontend/app/page.tsx:22-29` (troca `style={{ height: '100vh', ... }}` por `className="app-shell"` + resto dos estilos inline mantidos)

**Interfaces:** Nenhuma — mudança de CSS isolada, não afeta nenhum outro componente.

- [ ] **Step 1: Adicionar a classe `.app-shell` em `globals.css`**

Abrir `frontend/app/globals.css`, adicionar ao final do arquivo:

```css
.app-shell {
  height: 100vh;
  height: 100dvh;
}
```

A 2ª declaração sobrescreve a 1ª por cascata em navegadores que suportam
`dvh` (mobile moderno — Chrome/Safari Android e iOS recentes); onde não
suporta, o `100vh` de fallback continua valendo. Nenhuma mudança em desktop
(altura de janela não varia lá).

- [ ] **Step 2: Trocar o container raiz em `page.tsx`**

Em `frontend/app/page.tsx`, o `return` atual é:

```tsx
    <div
      style={{
        display: 'flex',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--chat-bg)',
      }}
    >
```

Trocar por:

```tsx
    <div
      className="app-shell"
      style={{
        display: 'flex',
        overflow: 'hidden',
        background: 'var(--chat-bg)',
      }}
    >
```

(`height: '100vh'` sai do `style` inline — a classe assume essa
responsabilidade; o resto do objeto de estilo permanece igual.)

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: build passa limpo (mesmo output de antes — `✓ Compiled
successfully`, `✓ Generating static pages`), sem erro de TypeScript/lint.

- [ ] **Step 4: Verificação visual manual (claude-in-chrome)**

Sem suite automatizada pra esse comportamento (a barra de endereço dinâmica
só existe em navegador móvel real/emulado, `100dvh` vs `100vh` não é
diferenciável de forma confiável em Chromium desktop headless do Playwright
— ver spec, seção Testagem). Verificação real:

1. Subir o app: `iniciar_frontend.bat` (backend na 8000).
2. Via `claude-in-chrome`, abrir `http://localhost:8000`, redimensionar a
   janela do navegador pra ~375×667 (tamanho de iPhone SE).
3. Confirmar visualmente: nenhum corte de conteúdo, input de mensagem
   visível e alcançável no rodapé, nenhuma barra de rolagem extra
   inesperada.
4. Redimensionar de volta pra tamanho desktop (~1280×800) e confirmar que
   nada mudou visualmente (regressão).

- [ ] **Step 5: Commit**

```bash
git add frontend/app/globals.css frontend/app/page.tsx
git commit -m "fix: altura de viewport mobile (100dvh com fallback 100vh)"
```

---

### Task 2: Header — menu "mais" abaixo de `sm` (640px)

**Files:**
- Modify: `frontend/components/Header.tsx` (import de ícone novo, novo state, restrutura JSX do bloco de controles à direita, novo componente `MoreMenu`)
- Create: `frontend/e2e/header-responsive.spec.ts`

**Interfaces:**
- Produces: `MoreMenu` (componente local a `Header.tsx`, não exportado, não
  consumido por nenhum outro arquivo) — `{ items: { icon: React.ReactNode;
  label: string; onClick: () => void }[]; onClose: () => void }`.

- [ ] **Step 1: Escrever os testes E2E que falham**

Criar `frontend/e2e/header-responsive.spec.ts`:

```ts
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
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Pré-requisito: backend de pé (`iniciar_frontend.bat` já builda e sobe em
`localhost:8000` — se já estiver rodando de sessão anterior, checar
`netstat -ano | grep :8000` antes de subir de novo).

Run: `cd frontend && npx playwright test e2e/header-responsive.spec.ts`
Expected: FAIL — `title="Mais opções"` não existe ainda em lugar nenhum, e
todos os 9 ícones aparecem direto mesmo em viewport 375px (comportamento
atual, sem breakpoint).

- [ ] **Step 3: Import do ícone novo**

Em `frontend/components/Header.tsx:4`, adicionar `MoreHorizontal` ao import
existente do `lucide-react`:

```tsx
import { Menu, Sun, Moon, User, Heart, Cpu, Database, Trash2, FolderOpen, RefreshCw, CheckCircle, XCircle, Loader2, Layers, GitGraph, LayoutGrid, Workflow, Download, ScrollText, MoreHorizontal } from 'lucide-react'
```

- [ ] **Step 4: Novo state `moreOpen`**

Em `frontend/components/Header.tsx`, junto aos outros `useState` de modal
(perto de `const [profileOpen, setProfileOpen] = useState(false)`,
linha ~21), adicionar:

```tsx
  const [moreOpen, setMoreOpen] = useState(false)
```

- [ ] **Step 5: Restruturar o bloco "Right controls"**

O bloco atual (`Header.tsx`, dentro do `<header>`, dos comentários `{/*
Right controls */}` até o fechamento da `<div>` que os contém — dos 8
`HeaderBtn` de Ferramentas/Exportar/NOC/Workflow/Modelos/RAG/Perfil/Audit
mais os 2 que ficam de fora, Health e tema) é substituído por:

```tsx
        {/* Right controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {/* Model selector */}
          {models.length > 0 && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '5px 10px',
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                marginRight: '4px',
              }}
            >
              <Cpu size={12} style={{ color: 'var(--accent)', flexShrink: 0 }} />
              <select
                value={currentModel}
                onChange={e => changeModel(e.target.value)}
                style={{
                  background: 'transparent',
                  color: 'var(--text-secondary)',
                  fontSize: '12px',
                  outline: 'none',
                  cursor: 'pointer',
                  maxWidth: '140px',
                }}
              >
                {models.map(m => (
                  <option key={m} value={m} style={{ background: '#1a1a1a' }}>{m}</option>
                ))}
              </select>
            </div>
          )}

          {/* Colapsáveis — visíveis a partir de sm (640px); em telas
              menores só via o botão "mais". iconBtnStyle define
              display:'flex' inline no HeaderBtn, por isso o toggle de
              visibilidade fica no wrapper (classe Tailwind), não no botão
              em si — inline style sempre vence classe CSS em especificidade. */}
          <div className="hidden sm:flex" style={{ alignItems: 'center', gap: '4px' }}>
            <HeaderBtn onClick={() => router.push('/ferramentas')} title="Ferramentas IA — 25 ferramentas especializadas">
              <LayoutGrid size={15} />
            </HeaderBtn>

            <HeaderBtn
              onClick={handleExport}
              title={
                exportState === 'done' ? 'Exportado! (baixado + salvo no Obsidian se configurado)'
                : exportState === 'error' ? 'Erro ao exportar — backend disponível?'
                : 'Exportar conversa (Markdown + Obsidian)'
              }
            >
              {exportState === 'saving' ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />
                : exportState === 'done' ? <CheckCircle size={15} style={{ color: '#4ade80' }} />
                : exportState === 'error' ? <XCircle size={15} style={{ color: '#f87171' }} />
                : <Download size={15} />}
            </HeaderBtn>

            <HeaderBtn onClick={() => setNocOpen(true)} title="NOC — Arvore de Raciocinio">
              <GitGraph size={15} />
            </HeaderBtn>

            <HeaderBtn onClick={() => setWorkflowOpen(true)} title="Workflow — DAG de Execução Paralela">
              <Workflow size={15} />
            </HeaderBtn>

            <HeaderBtn onClick={() => setModelsOpen(true)} title="Modelos por Especialista">
              <Layers size={15} />
            </HeaderBtn>

            <HeaderBtn onClick={() => setRagOpen(true)} title="Indexação de documentos (RAG)">
              <Database size={15} />
            </HeaderBtn>

            <HeaderBtn onClick={() => setProfileOpen(true)} title="Perfil">
              <User size={15} />
            </HeaderBtn>

            <HeaderBtn onClick={() => setAuditOpen(true)} title="Audit log / Tracing">
              <ScrollText size={15} />
            </HeaderBtn>
          </div>

          {/* Botão "mais" — só abaixo de sm, abre menu com as 8 ações acima */}
          <div className="sm:hidden" style={{ position: 'relative' }}>
            <HeaderBtn onClick={() => setMoreOpen(o => !o)} title="Mais opções">
              <MoreHorizontal size={15} />
            </HeaderBtn>
            {moreOpen && (
              <MoreMenu
                onClose={() => setMoreOpen(false)}
                items={[
                  { icon: <LayoutGrid size={15} />, label: 'Ferramentas IA', onClick: () => router.push('/ferramentas') },
                  { icon: <Download size={15} />, label: 'Exportar conversa', onClick: handleExport },
                  { icon: <GitGraph size={15} />, label: 'NOC — Árvore de Raciocínio', onClick: () => setNocOpen(true) },
                  { icon: <Workflow size={15} />, label: 'Workflow — DAG', onClick: () => setWorkflowOpen(true) },
                  { icon: <Layers size={15} />, label: 'Modelos por Especialista', onClick: () => setModelsOpen(true) },
                  { icon: <Database size={15} />, label: 'RAG — Documentos', onClick: () => setRagOpen(true) },
                  { icon: <User size={15} />, label: 'Perfil', onClick: () => setProfileOpen(true) },
                  { icon: <ScrollText size={15} />, label: 'Audit log / Tracing', onClick: () => setAuditOpen(true) },
                ]}
              />
            )}
          </div>

          <HeaderBtn onClick={() => setHealthOpen(true)} title="Status do sistema">
            <Heart size={15} />
          </HeaderBtn>

          <HeaderBtn onClick={toggleTheme} title={theme === 'dark' ? 'Tema claro' : 'Tema escuro'}>
            {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
          </HeaderBtn>
        </div>
```

Nota: o item do menu usa `handleExport` diretamente como `onClick` — igual
ao `HeaderBtn` de exportar já fazia, o estado de loading/sucesso/erro
(`exportState`) continua refletindo no ícone do `HeaderBtn` de desktop
normalmente; o item do menu mobile não replica o ícone de estado (só o
ícone `Download` fixo) — comportamento levemente mais simples no mobile, é
aceitável (não estava no escopo da spec pedir paridade de estado visual,
só de funcionalidade).

- [ ] **Step 6: Componente `MoreMenu`**

Em `frontend/components/Header.tsx`, logo depois da função `HeaderBtn`
(depois do fechamento de `applyHover`, antes do comentário `/* ── Modal
base ── */`), adicionar:

```tsx
function MoreMenu({ items, onClose }: { items: { icon: React.ReactNode; label: string; onClick: () => void }[]; onClose: () => void }) {
  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 59 }} />
      <div
        role="menu"
        aria-label="Mais opções"
        style={{
          position: 'absolute',
          top: '100%',
          right: 0,
          marginTop: '6px',
          background: 'var(--surface)',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-sm)',
          boxShadow: '0 12px 32px rgba(0,0,0,0.4)',
          zIndex: 60,
          minWidth: '220px',
          overflow: 'hidden',
        }}
        className="anim-fade-up"
      >
        {items.map((item, i) => (
          <button
            key={i}
            onClick={() => { item.onClick(); onClose() }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              width: '100%',
              padding: '10px 14px',
              fontSize: '13px',
              color: 'var(--text-secondary)',
              background: 'transparent',
              textAlign: 'left',
              cursor: 'pointer',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </div>
    </>
  )
}
```

O overlay `position:fixed inset:0` (z-index 59, abaixo do menu em 60) fecha
o menu ao clicar fora — mesmo padrão de `onClick={e => { if (e.target ===
e.currentTarget) onClose() }}` que os modais já usam, mas aqui qualquer
clique fora fecha (não precisa checar `e.target`, o overlay inteiro é a
área "fora").

- [ ] **Step 7: Build**

Run: `cd frontend && npm run build`
Expected: build passa limpo, sem erro de TypeScript (o tipo de `items` no
`MoreMenu` precisa bater com o array literal passado — `React.ReactNode`
pros ícones, `string` pro label, `() => void` pro onClick).

- [ ] **Step 8: Rodar os testes E2E e confirmar que passam**

Run: `cd frontend && npx playwright test e2e/header-responsive.spec.ts`
Expected: PASS — os 4 testes (3 mobile + 1 desktop).

- [ ] **Step 9: Rodar toda a suite E2E (regressão)**

Run: `cd frontend && npx playwright test`
Expected: PASS em todos os specs existentes (`app-shell`,
`chat-full-response`, `chat-optimistic`, `wake-word`) além do novo — nada
quebrou no restante do app por causa da restruturação do header.

- [ ] **Step 10: Commit**

```bash
git add frontend/components/Header.tsx frontend/e2e/header-responsive.spec.ts
git commit -m "feat: header colapsa icones secundarios em menu 'mais' abaixo de 640px"
```

---

### Task 3: Validação visual final (claude-in-chrome)

**Files:** nenhum (validação).

- [ ] **Step 1: Subir o app**

Checar se já tem processo na 8000 (`netstat -ano | grep :8000`); se não,
`iniciar_frontend.bat`.

- [ ] **Step 2: Testar em viewport mobile real via claude-in-chrome**

Redimensionar janela pra 375×667. Confirmar:
- Header mostra só: toggle sidebar, seletor de modelo, botão "mais",
  Health, tema.
- Clicar "mais" abre o menu, todos os 8 itens legíveis e clicáveis (testar
  ao menos 1 — ex: "Perfil" — abre o modal correto).
- Nenhum corte de conteúdo na tela (Task 1 — `100dvh`).
- Scroll da conversa e input de mensagem funcionam normalmente.

- [ ] **Step 3: Testar em viewport desktop (regressão)**

Redimensionar de volta pra ~1280×800. Confirmar visualmente idêntico ao
`docs/screenshots/*.jpg` já existentes — todos os 9 ícones em linha, sem
botão "mais" visível.

- [ ] **Step 4: Reportar resultado**

Sem commit nesse passo (validação pura). Se algo não bater, voltar pra Task
2 e ajustar antes de considerar o plano concluído.
