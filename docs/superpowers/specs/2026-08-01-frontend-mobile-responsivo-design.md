# Frontend responsivo mobile

## Contexto

Frontend Next.js (`frontend/`) é usado hoje só em desktop. Usuário quer usar
em celular também — motivação real: projeto já tem acesso remoto via
Tailscale preparado (sessão 2026-07-31), então o app fica alcançável fora da
LAN local, inclusive do celular.

Inspecionado o código atual (não só a impressão visual dos screenshots em
`docs/screenshots/`) e achados 2 problemas reais de responsividade — o resto
(sidebar drawer, input de mensagem) já está adequado pra mobile:

1. **`app/page.tsx:25`**: container raiz usa `height: '100vh'` inline. Bug
   clássico mobile — a barra de endereço do navegador (Chrome/Safari mobile)
   muda de altura ao rolar, e `100vh` não acompanha essa mudança, cortando
   conteúdo ou deixando espaço vazio embaixo.
2. **`components/Header.tsx`**: 9 botões de ícone (Ferramentas, Exportar,
   NOC, Workflow, Modelos por Especialista, RAG, Perfil, Health, Audit) +
   seletor de modelo (`<select>`), todos numa única linha flex sem nenhum
   breakpoint — em telas de ~360-400px (celular) não cabe, sem mecanismo de
   colapso/overflow.

Fora do escopo: sidebar (`components/Sidebar.tsx`) já tem drawer mobile
funcional (`lg:hidden`/`lg:relative`, overlay); `MessageInput` já está no
fluxo flex normal (não `position: fixed`), então não conflita com o teclado
virtual. Nenhum redesenho visual — cores, tipografia, espaçamento existentes
ficam como estão.

**AVISO do projeto** (`frontend/AGENTS.md`): esse Next.js (16.2.9) tem
mudanças que podem divergir do treino do modelo — checar
`node_modules/next/dist/docs/` antes de usar qualquer API não já usada no
projeto.

## Decisão

### 1. Altura da viewport — CSS class em vez de inline

`globals.css` ganha:

```css
.app-shell { height: 100vh; height: 100dvh; }
```

`app/page.tsx` troca o `style={{ height: '100vh', ... }}` do container raiz
por `className="app-shell"` + o resto dos estilos que não mudam permanece
inline (ou também migra pra classe, decisão de implementação, não de design).
`100dvh` é sobrescrito por cascata sobre o `100vh` em navegadores que
suportam (a maioria dos mobile modernos); onde não suporta, o `100vh` de
fallback continua valendo — sem regressão em navegador antigo.

### 2. Header — menu "mais" abaixo do breakpoint `sm` (640px, Tailwind)

Divide os botões de ícone em dois grupos:

- **Sempre visíveis** (todas as larguras): toggle sidebar (já existe,
  `lg:hidden`), seletor de modelo, tema (Sun/Moon), Health (❤️ — dashboard
  de performance, o mais checado segundo o uso registrado nas memórias de
  sessão).
- **Colapsam num botão `⋯`** abaixo de `sm:` — abre um dropdown simples
  (mesmo padrão visual/z-index dos modais já existentes, `position: fixed`
  centralizado ou um popover ancorado no botão, decisão de implementação):
  Ferramentas, Exportar, NOC (Árvore de Raciocínio), Workflow (DAG), Modelos
  por Especialista, RAG, Perfil, Audit log.
- Acima de `sm:`: comportamento idêntico ao atual, todos os 9 ícones em
  linha — **nenhuma mudança visual em desktop**.

O botão `⋯` e o dropdown reusam os componentes/estilos já existentes em
`Header.tsx` (`iconBtnStyle`, `HeaderBtn`, padrão de modal) — sem introduzir
biblioteca nova.

## Testagem

Sem suite automatizada de viewport (projeto não tem Playwright configurado
pra breakpoints, só E2E funcional — fora de escopo adicionar aqui). Validação
manual real via `claude-in-chrome`: redimensionar janela do browser pra
largura de celular (~375px, iPhone SE/12 mini como referência) e conferir
visualmente que (a) nada corta/estoura, (b) menu `⋯` abre e cada ação
funciona, (c) em desktop (>640px) nada mudou.

## Fora de escopo

Redesenho visual (cores/tipografia/espaçamento), barra de navegação inferior
tipo app nativo, mudanças em `Sidebar.tsx`/`MessageInput.tsx` (já adequados),
PWA/manifest/instalável, testes automatizados de viewport.
