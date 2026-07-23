# 🤖 Agente IA Local — v1.3

> Assistente de IA autônomo rodando **100% na sua máquina** — sem APIs externas, sem custos por token, sem dados saindo do seu PC.

Usa Ollama para inferência local, arquitetura ReAct para raciocínio passo a passo, e 32 ferramentas reais para executar tarefas complexas.

**v1.0** — Tiered Memory · Reflection Loop · Multi-model por especialista · WASM/Docker Sandbox · Visual Browser · NOC Dashboard + HITL
**v1.1** — Geração de imagem local (SD-turbo) · LanceDB (substituiu ChromaDB) · Export de conversa pro Obsidian · Auto-detect de nível técnico · Plugin manager sandboxado
**v1.2** — Refino visual do frontend · Fontes de pesquisa ao vivo no chat · `generate_image` com seed/múltiplas imagens/upscale
**v1.3** — Testes automatizados (pytest) · HITL por camada de risco · Isolamento least-privilege por especialista · Prompt-injection guard · Schema validado por tool · Circuit breaker · Eval harness + git hook pre-push · Memória episódica cross-sessão · Plan-then-Execute persistido em disco · Execução proativa (`schedule_task`) · Guards de fidelidade da resposta final

---

## ✨ O que ele faz

```
Você: pesquise o preço do bitcoin, gere um gráfico e salve o relatório

IA:   [Raciocínio] Vou buscar o preço, gerar o chart e salvar...
      [Ação] web_search("bitcoin price today BRL")
      [Resultado] Bitcoin: R$ 612.450 (alta 2,3%)
      [Ação] generate_chart(dados, type="line", title="Bitcoin 7 dias")
      [Ação] write_file("relatorio_bitcoin.md", conteudo)
      ✅ Relatório salvo com gráfico em relatorio_bitcoin.md
```

**Funciona com qualquer modelo Ollama** — llama3, qwen2.5, mistral, deepseek, gemma...

---

## 🎯 Funcionalidades

### Interface
- Chat estilo Claude/ChatGPT — dark mode, sidebar com histórico agrupado por data
- Streaming token a token com cursor animado
- **ThinkingSteps collapsível** — veja o raciocínio completo (Thought → Action → Observation)
- **Auto-correção** — quando uma ferramenta falha, o agente analisa o erro e tenta novamente (até 3x)
- Upload de arquivos, copiar resposta, regenerar, feedback 👍👎
- Modo voz: fale para o agente (STT via Whisper) e ouça a resposta (TTS)
- Troca de modelo em runtime via dropdown

### RAG — Documentos Locais
- Indexe PDF, TXT, Markdown e DOCX
- **Busca híbrida**: 65% semântica (LanceDB) + 35% palavras-chave (BM25) — melhor precisão para termos técnicos
- Arraste arquivos ou aponte uma pasta inteira para indexar
- Auto-indexação: coloque arquivos em `workspace/` e eles são indexados automaticamente

### Dashboard de Performance
- **TPS** — tokens por segundo gerados pela GPU
- **TTFT** — latência até o primeiro token (ms)
- **Uso do contexto** — % do context window usado (alerta em >80%)
- **VRAM** — barra de uso de memória da GPU + temperatura + power draw
- **Taxa de sucesso por ferramenta** — últimos 7 dias
- **Sandbox status** — Docker isolado vs. fallback local

### v1.0 — Funcionalidades Avançadas

| Fase | Feature |
|---|---|
| 1 | **Tiered Memory** — Redis (curta), LanceDB+BM25 (episódica), grafo semântico (longo prazo) |
| 2 | **Reflection Loop** — critic LLM avalia resposta (score 1-5), retry se abaixo do threshold |
| 3 | **Multi-model** — modelo diferente por especialista, troca sem restart via UI |
| 4 | **Sandbox WASM/Docker** — `run_python` isolado: WASM (boot instantâneo) → Docker (sem rede, 256MB RAM, sem root) → local |
| 5 | **Visual Browser** — Playwright + VLM: agente vê páginas como imagens, screenshots inline no chat |
| 6 | **NOC + HITL** — React Flow com árvore de raciocínio, Human-in-the-Loop para ferramentas sensíveis |

### Multi-agente
O agente principal delega tarefas para especialistas:
- **Pesquisador** — web, APIs, síntese de informações
- **Arquivos** — leitura, escrita, RAG, Obsidian
- **Código** — Python, SQL, terminal, git
- **Computador** — screenshot, teclado, mouse, browser
- **Comunicação** — email, Notion, Slack, Google Drive
- **Professor** — tutor adaptativo com quizzes e exercícios
- **Dados** — CSV, Excel, gráficos, análise estatística

### Perfil de Usuário
Salva nível técnico (iniciante → especialista) e tom preferido. O agente adapta as explicações automaticamente.
**Auto-detecção de nível**: o agente ajusta `tech_level` sozinho lendo jargão técnico, blocos de código e frases de dificuldade nas mensagens (sem custo de LLM extra) — some pra "avançado" se você manda termos técnicos, desce pra "iniciante" se pergunta "o que é X". Define o nível manualmente no perfil e a auto-detecção para de mexer.

### Agendamento
Tarefas recorrentes via `SCHEDULED_TASKS` em `config.py`:
```python
SCHEDULED_TASKS = [
    {"label": "Notícias", "task": "pesquise notícias de tech hoje", "hour": 8, "minute": 0},
]
```

---

## 🛠️ 32 Ferramentas

O agente decide sozinho qual usar baseado na tarefa. Todo input é validado contra schema antes de executar (`tools/_schema.py`), e tools que ingerem conteúdo externo (web/páginas/arquivos) passam por guard de prompt-injection (`tools/_security.py`).

| Categoria | Ferramentas |
|-----------|------------|
| **Web** | `web_search`, `fetch_page`, `http_request`, `browser` (Playwright) |
| **Arquivos** | `read_file`, `write_file`, `list_directory` |
| **Código** | `run_python` (sandbox), `run_sql`, `terminal` (sandboxed), `git` |
| **Dados** | `read_spreadsheet` (CSV/Excel), `generate_chart` (matplotlib), `generate_report`, `rag_search`, `get_crypto` |
| **Visão** | `analyze_image` (LLaVA multimodal), `generate_image` (Stable Diffusion local — sd-turbo) |
| **Memória** | `remember_fact`, `save_note` (Obsidian) |
| **Computer Use** | `screenshot`, `keyboard`, `mouse`, `clipboard` |
| **Automação** | `schedule_task` (agente cria/lista/remove suas próprias tarefas agendadas via chat) |
| **Integrações** | `email`, `notion`, `slack`, `discord_notify` (webhook configurado e testado), `google_drive`, `get_currency` |
| **Dev/teste** | `echo` (smoke test, não usado em produção) |

### Sandbox de segurança
- `run_python` → hierarquia **WASM → Docker → local**:
  - **WASM** (`wasmtime` + CPython/WASI) — sem rede, memória limitada, `/workspace` read-only, timeout via epoch interruption. Boot quase instantâneo (módulo compilado uma vez e cacheado) — sem overhead de `docker run` a cada chamada. Só stdlib (sem numpy/pandas)
  - **Docker** (se WASM não disponível) — isolado, sem rede, 256MB RAM, 1 CPU, user 65534, sem root — numpy/pandas/matplotlib/scipy disponíveis na imagem `ia-sandbox`
  - **Local** (fallback final, com aviso) — se nem WASM nem Docker disponíveis
- `terminal` → whitelist de comandos permitidos
- `http_request` → SSRF bloqueado (IPs privados bloqueados)
- `read_file` → whitelist de pastas configurável
- `browser` → headless Chromium, screenshot analisado por VLM local

```bash
# Sandbox WASM (recomendado — mais rápido, não precisa Docker Desktop rodando)
pip install wasmtime
download_wasm_sandbox.bat

# Sandbox Docker com numpy/pandas/matplotlib/scipy (usado se WASM não disponível)
build_sandbox.bat
```

---

## 🚀 Instalação

### Pré-requisitos
- [Ollama](https://ollama.com) instalado e rodando
- Python 3.10+
- Node.js 18+
- Docker Desktop (opcional — sandbox `run_python` usa WASM primeiro, Docker é fallback)

### 1. Clonar e instalar dependências

```bash
git clone https://github.com/SEU_USUARIO/agente-ia-local
cd agente-ia-local

# Dependências Python
pip install -r requirements.txt

# Playwright (browser automation)
playwright install chromium

# Dependências do frontend
cd frontend && npm install && cd ..
```

### 2. Baixar um modelo

```bash
# Recomendado — melhor qualidade em tarefas compostas (4.7GB VRAM)
ollama pull qwen2.5:7b

# Alternativa mais rápida, mas ignora instrução composta com mais frequência (2GB VRAM)
ollama pull llama3.2:3b

# Visual Browser — VLM local (cabe em 2GB VRAM)
ollama pull moondream:1.8b

# Embeddings locais — melhora busca RAG em português
ollama pull nomic-embed-text
```

### 3. Configurar

Copie e edite as configurações:

```bash
cp config.example.py config.py
```

Edite `config.py`:
```python
OLLAMA_MODEL = "qwen2.5:7b"   # modelo escolhido
OBSIDIAN_BASE = r"C:\Seu\Vault\Obsidian"  # opcional
```

### 4. Iniciar

```bash
# Windows — duplo clique ou:
.\iniciar_frontend.bat

# Linux/Mac:
python -m uvicorn api:app --port 8000 &
cd frontend && npm run dev
```

Abrir: **http://localhost:3000**

**Alternativa sem Node.js** (UI HTML simples):
```bash
.\iniciar.bat
# Abrir: http://localhost:8000
```

---

## ⚙️ Configuração

Tudo em `config.py`:

```python
# Modelos
OLLAMA_MODEL      = "qwen2.5:7b"     # qualquer modelo Ollama
VISION_MODEL      = "moondream:1.8b" # VLM para browser visual (cabe em 2GB VRAM)
MANAGER_MODEL     = ""               # modelo para roteamento — vazio = herda OLLAMA_MODEL

# Performance
MAX_STEPS         = 8               # iterações ReAct por tarefa
NUM_PREDICT       = 700             # tokens por step (baixo → trunca → mais loops)
NUM_CTX           = 4096            # context window
TEMPERATURE       = 0.1

# Limites de segurança
TOOL_TIMEOUT      = 30              # segundos por ferramenta
MAX_TOOL_CALLS    = 15              # chamadas por tarefa
MAX_TOOL_RETRIES  = 3               # tentativas de auto-correção
TASK_TIMEOUT      = 300             # timeout total da tarefa

# Reflection Loop
REFLECTION_ENABLED   = True
REFLECTION_THRESHOLD = 2            # retry se score <= 2 (1-5)

# Human-in-the-Loop — por camada de risco (read/write/destructive), não lista fixa de tools
HITL_ENABLED         = False
HITL_GATE_TIERS      = ["destructive"]   # quais tiers pausam pra aprovação quando HITL_ENABLED=True

# Especialistas com modelos diferentes
SPECIALIST_MODELS = {
    # "codigo": "qwen2.5-coder:7b",
}

# Geração de imagem (generate_image) — requer pip install torch diffusers accelerate
IMAGE_GEN_MODEL   = "stabilityai/sd-turbo"
IMAGE_GEN_DEVICE  = "auto"          # "auto" | "cuda" | "cpu"

# Autenticação (deixe vazio para desativar)
AUTH_PASSWORD     = ""

# Pastas que o agente pode ler
ALLOWED_READ_DIRS = [
    r"C:\Users\SeuUsuario\Desktop",
    r"C:\Users\SeuUsuario\Documents",
]
```

---

## 🔌 Adicionar nova ferramenta

Crie `tools/minha_tool.py`:

```python
class MinhaTool:
    name = "minha_tool"
    description = "Descrição do que faz. Input: {'param': 'valor'}"

    def run(self, params: dict) -> str:
        valor = params.get("param", "")
        return f"Resultado: {valor}"
```

Salve o arquivo — é detectado e carregado automaticamente pelo plugin system. Sem reiniciar o servidor.

### Plugins de terceiros (via URL) — opcional, desligado por padrão

`plugin_manager.py` instala ferramentas publicadas por terceiros, com verificação de integridade e execução sandboxada. Diferente de `tools/*_tool.py` (código de primeira parte, roda direto no processo), plugin é código não confiável — instalação é sempre manual, e a execução acontece dentro do [sandbox WASM](#sandbox-de-segurança), nunca via `import` no processo do agente.

```bash
python plugin_manager.py stage <manifest_url>    # baixa e verifica o hash — nada roda ainda
python plugin_manager.py list                     # staged vs approved
python plugin_manager.py approve <nome>            # só depois de VOCÊ ler o código
python plugin_manager.py run <nome> '{"n": 21}'    # exige PLUGINS_ENABLED=True em config.py
```

Ver a docstring de `plugin_manager.py` pro modelo de segurança completo. Nunca é chamado pelo agente sozinho — instalar plugin de terceiro é decisão sua, não dele.

---

## 🔒 Segurança e Privacidade

- **Zero dados externos** — nenhuma chamada para OpenAI, Anthropic ou qualquer API de IA
- **Sandbox** — `run_python` isolado (WASM → Docker → local), sem acesso à rede ou filesystem do host
- **Whitelist de comandos** — `terminal` só executa comandos explicitamente permitidos
- **SSRF protection** — `http_request` bloqueia IPs privados (127.x, 192.168.x, 10.x)
- **Whitelist de pastas** — `read_file` e `list_directory` só acessam pastas configuradas
- **Audit log** — toda chamada de ferramenta é gravada em SQLite (`workspace/audit.db`)
- **Rate limiting** — 60 req/min por IP
- **JWT opcional** — ative com `AUTH_PASSWORD` em `config.py`
- **HITL por camada de risco** — `TOOL_RISK_TIERS` classifica cada tool em read/write/destructive; `HITL_GATE_TIERS` define quais tiers pausam pra aprovação humana quando `HITL_ENABLED=True` (substitui lista fixa de tool names, que tinha bug de nome divergente)
- **Isolamento por especialista (least privilege)** — tarefa multi-domínio libera só a união das tools dos domínios detectados, não o toolset inteiro do sistema
- **Prompt-injection guard** — tools que ingerem conteúdo externo (web/páginas/arquivos) sanitizadas contra instrução embutida no conteúdo
- **Schema por tool** — input validado antes de executar, rejeita malformado antes de chegar na tool
- **Circuit breaker** — para de tentar tool quebrada repetidamente; alerta de taxa de erro alta no Dashboard
- **Eval harness + git hook pre-push** — golden tasks rodam contra o agente real (Ollama) automaticamente antes de permitir push

> ⚠️ **Não commite** `gdrive_credentials.json`, `gdrive_token.json`, `workspace/` ou `agent_memory.json` — esses arquivos contêm dados pessoais e tokens OAuth.

---

## 🗺️ Arquitetura

```
Browser ──WebSocket──► FastAPI (api.py)
                            │
                    OrchestratorAgent
                    (classifica tarefa)
                            │
          ┌─────────┬───────┼───────┬──────────┐
      pesquisador  arquivos codigo computador comunicacao
                            │
                       ReActAgent
                  Thought → Action → Observation
                       [auto-correção]
                            │
                     tool_loader.py
                     32 tools (plugins)
                            │
               memory.py  rag.py  user_profile.py
               LanceDB    BM25    audit.db
```

---

## 📁 Estrutura do projeto

```
agente-ia-local/
├── api.py               # FastAPI + WebSocket + todos endpoints
├── agent.py             # ReActAgent + auto-correção
├── orchestrator.py      # Multi-agente (6 especialistas)
├── llm.py               # Cliente Ollama (streaming, TPS/TTFT tracking)
├── rag.py               # LanceDB + BM25 híbrido (PDF/TXT/MD/DOCX)
├── vector_store.py      # wrapper LanceDB (upsert/query/delete por id ou filtro)
├── embeddings.py        # embedder compartilhado — Ollama (nomic-embed-text) ou fastembed local
├── memory.py            # Persistência de sessões + backup
├── user_profile.py      # Perfil do usuário
├── tool_loader.py       # Plugin system (auto-carrega tools/)
├── scheduler.py         # Tarefas agendadas
├── watcher.py           # Auto-indexação de arquivos novos
├── audit.py             # Audit log SQLite
├── voice.py             # STT (Whisper) + TTS (pyttsx3)
├── auth.py              # JWT auth
├── config.py            # ← configuração central
├── config.example.py    # template sem dados sensíveis
├── requirements.txt
├── iniciar.bat          # Backend (porta 8000)
├── iniciar_frontend.bat # Backend + Next.js (porta 3000)
├── tools/               # 32 ferramentas — adicione arquivos aqui
├── tests/               # pytest — suite automatizada
├── eval/                # golden tasks (eval harness) — roda contra o agente real (Ollama)
├── hooks/                # git hook pre-push — roda eval/golden_tasks.py antes de liberar push
├── sandbox_wasm/        # binário CPython/WASI (baixado por download_wasm_sandbox.bat)
└── frontend/            # Next.js 16 + React 19 + TypeScript + Tailwind v4
```

---

## 📦 Requirements

```
# requirements.txt
requests
ddgs
fastapi
uvicorn[standard]
beautifulsoup4
python-multipart
lancedb
fastembed
pypdf
watchdog
pyjwt
faster-whisper
pyttsx3
pyautogui
Pillow
pyperclip
playwright
redis
networkx
wasmtime

# generate_image_tool (Stable Diffusion local) — opcional, downloads grandes
torch
diffusers
accelerate

# generate_chart_tool
matplotlib

# testes (dev) — rodar com: pytest
pytest
```

> `torch`/`diffusers`/`accelerate` só são necessários pra `generate_image`. No Windows com GPU, instale o `torch` com suporte CUDA **antes** de rodar `pip install -r requirements.txt` ([pytorch.org/get-started/locally](https://pytorch.org/get-started/locally)) — senão cai pra CPU automaticamente.
>
> `wasmtime` habilita o sandbox WASM do `run_python` — depois de instalar, rode `download_wasm_sandbox.bat` uma vez pra baixar o binário CPython/WASI (~26MB, não vai pro git).
>
> `redis` é opcional — `ShortTermMemory` cai pra dict em memória se o Redis não estiver rodando. `networkx` é usado pelo Knowledge Graph.

---

## 🗺️ Roadmap

### v1.0 — Entregue ✅
- [x] Tiered Memory (Redis + LanceDB + Knowledge Graph)
- [x] Reflection Loop (critic LLM, score 1-5, retry automático)
- [x] Multi-model por especialista (troca sem restart)
- [x] Docker Sandbox para `run_python` (isolamento total)
- [x] WASM sandbox para `run_python` (wasmtime + CPython/WASI) — boot quase instantâneo, preferido sobre Docker quando disponível
- [x] Visual Browser (Playwright + VLM, screenshots inline no chat)
- [x] NOC Dashboard — React Flow thought tree
- [x] Human-in-the-Loop (pausa agente, usuário aprova/rejeita)

### v1.1 — Entregue ✅
- [x] Geração de imagens — `generate_image` (Stable Diffusion local, sd-turbo, GPU com fallback CPU) — código pronto, imagem sai como markdown inline (mesmo padrão do `browser_tool`)
- [x] Exibir imagens geradas inline no chat (além de screenshots) — `generate_chart` agora retorna markdown com `_img_url` também; endpoint `/workspace/img/` passou a aceitar subpasta (`charts/`)
- [x] Export de conversa para Markdown/Obsidian — botão no header (`Download`) baixa a conversa como `.md` e salva cópia em `Gabriel/Projetos/Agente IA Local/Conversas/` no Obsidian (`POST /export/conversation`); funciona mesmo sem Obsidian configurado (download local sempre acontece). Toda sessão automática, export manual e `save_note` linkam a nota nova sozinhos no índice `Conversas.md` (2026-07-21)
- [x] Auto-detect nível técnico do usuário por padrões de conversa — heurística sem LLM (jargão técnico, blocos de código, frases de "não entendi") em `user_profile.py`, EMA de score ajusta `tech_level` a cada mensagem; para automaticamente se o usuário define o nível manualmente no perfil

### v1.2 — Entregue ✅
- [x] Refino visual do frontend (modais com blur, header agrupado em clusters, feedback tátil nos botões)
- [x] Fontes de pesquisa ao vivo no chat — painel "Fontes" agrega `web_search`/`fetch_page` sem duplicar URL
- [x] `generate_image` — `seed` (reprodutível), `num_images` (1-4), `upscale_factor` (1-4, Lanczos)

### v1.3 — Entregue ✅
- [x] Suite de testes automatizados (pytest) — `tests/`
- [x] HITL por camada de risco (`TOOL_RISK_TIERS`/`HITL_GATE_TIERS`) — corrigiu bug de `send_email` nunca disparando HITL
- [x] Isolamento least-privilege por especialista em tarefa multi-domínio
- [x] Prompt-injection guard nas tools que ingerem conteúdo externo
- [x] Schema validado por tool antes de executar
- [x] Circuit breaker por tool + eval harness (golden tasks) + git hook pre-push
- [x] Memória episódica cross-sessão — recall da sessão anterior mesmo após TTL do short-term
- [x] Plan-then-Execute persistido em disco — retoma tarefa composta se o processo cair
- [x] Execução proativa — tool `schedule_task`, agente se auto-agenda via chat
- [x] Guards de fidelidade — Final Answer não pode contradizer um erro real na Observation
- [x] Self-consistency (best-of-2) na Reflection Loop

### v1.4 — Entregue ✅ (2026-07-23, hardening)
- [x] Auditoria de segurança em todas as tools "destructive" — sandbox-escape corrigido em `terminal`/`git`, SSRF corrigido em `browser`, query injection corrigida em `google_drive`, `keyboard`/`mouse` passam a exigir aprovação humana sempre (sem whitelist possível pra controle bruto de tecla/clique)
- [x] CI (GitHub Actions) rodando pytest a cada push/PR + secret-scanning (gitleaks) — achou e corrigiu drift real: `config.example.py` estava desatualizado o bastante pra quebrar qualquer clone novo
- [x] `requirements.txt` com versões pinadas; 6 libs listadas mas não instaladas de verdade, corrigido
- [x] Fix de disputa de VRAM entre Ollama e `generate_image` na GPU
- [x] Circuit breaker com cooldown por tool (credencial faltando ≠ rede transiente) em vez de 5min fixo pra tudo
- [x] Dashboard mostra taxa de reflection-rewrite (quanto o critic reprova a 1ª resposta)
- [x] Retenção manual pra `audit.db`/`traces.db` (cresciam sem limite)
- [x] mypy configurado — achou e corrigiu bug real (`log` indefinido quebrando troca de modelo pela API)
- [x] `discord_notify` — webhook configurado e testado em produção

### Futuro
- [x] LanceDB — substituiu ChromaDB (embutido/serverless, sem servidor separado) em `memory.py` (sessions/facts) e `rag.py` (pdf_chunks) — embeddings via `embeddings.py` (Ollama nomic-embed-text, fallback fastembed local), veja `migrate_chroma_to_lancedb.py` pra portar dados antigos
- [ ] WhatsApp Business API
- [x] WASM sandbox (alternativa ao Docker — boot instantâneo) — feito, ver Fase 4
- [x] Plugin marketplace (design + sandboxing) — `plugin_manager.py`: instala manual (nunca o agente sozinho), hash SHA-256 pinado no manifest (bloqueia supply-chain attack se o código mudar após publicado), stage→approve como dois passos separados, execução dentro do sandbox WASM (`PLUGINS_ENABLED=False` por padrão). Falta: UI de instalação/descoberta de plugins — hoje é só CLI

---

## 🙋 FAQ

**Precisa de GPU?**
Não obrigatório, mas recomendado. Com CPU funciona — só mais lento. `llama3.2:3b` roda ok em CPU moderna.

**Funciona no Mac/Linux?**
Backend sim. Os `.bat` são Windows — no Mac/Linux use os comandos diretos do Python/npm.

**Qual modelo usar?**
- `qwen2.5:7b` — recomendado, melhor qualidade geral e segue instrução composta (4.7GB VRAM)
- `llama3.2:3b` — mais rápido mas ignora instrução composta com mais frequência, bom só pra tarefas simples (2GB VRAM)
- `deepseek-r1:8b` — melhor raciocínio (5GB VRAM)
- `moondream:1.8b` — VLM para visual browser (1.5GB VRAM, pull separado)
- `nomic-embed-text` — embeddings locais para RAG (pull separado)

**Docker é obrigatório?**
Não. Sem Docker o `run_python` executa localmente com timeout de 10s. Com Docker tem isolamento total.

**Como integrar Google Drive?**
Ver seção de configuração avançada na [wiki](../../wiki).

---

## 📄 Licença

MIT — use, modifique e distribua livremente.

---

<div align="center">

Feito com 🧠 + Ollama + FastAPI + Next.js

**100% local · 100% privado · 0 custos por token**

</div>
