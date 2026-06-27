# 🤖 Agente IA Local — v1.0

> Assistente de IA autônomo rodando **100% na sua máquina** — sem APIs externas, sem custos por token, sem dados saindo do seu PC.

Usa Ollama para inferência local, arquitetura ReAct para raciocínio passo a passo, e 27 ferramentas reais para executar tarefas complexas.

**v1.0** — Tiered Memory · Reflection Loop · Multi-model por especialista · Docker Sandbox · Visual Browser · NOC Dashboard + HITL

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
- **Busca híbrida**: 65% semântica (ChromaDB) + 35% palavras-chave (BM25) — melhor precisão para termos técnicos
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
| 1 | **Tiered Memory** — Redis (curta), ChromaDB+BM25 (episódica), grafo semântico (longo prazo) |
| 2 | **Reflection Loop** — critic LLM avalia resposta (score 1-5), retry se abaixo do threshold |
| 3 | **Multi-model** — modelo diferente por especialista, troca sem restart via UI |
| 4 | **Docker Sandbox** — `run_python` em container isolado (sem rede, 256MB RAM, sem root) |
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

### Agendamento
Tarefas recorrentes via `SCHEDULED_TASKS` em `config.py`:
```python
SCHEDULED_TASKS = [
    {"label": "Notícias", "task": "pesquise notícias de tech hoje", "hour": 8, "minute": 0},
]
```

---

## 🛠️ 27 Ferramentas

O agente decide sozinho qual usar baseado na tarefa.

| Categoria | Ferramentas |
|-----------|------------|
| **Web** | `web_search`, `fetch_page`, `http_request`, `browser` (Playwright) |
| **Arquivos** | `read_file`, `write_file`, `list_directory` |
| **Código** | `run_python` (Docker sandbox), `run_sql`, `terminal` (sandboxed), `git` |
| **Dados** | `read_spreadsheet` (CSV/Excel), `generate_chart` (matplotlib), `rag_search` |
| **Visão** | `analyze_image` (LLaVA multimodal) |
| **Memória** | `remember_fact`, `save_note` (Obsidian) |
| **Computer Use** | `screenshot`, `keyboard`, `mouse`, `clipboard` |
| **Integrações** | `email`, `notion`, `slack`, `google_drive`, `get_currency` |

### Sandbox de segurança
- `run_python` → Docker isolado (sem rede, 256MB RAM, 1 CPU, user 65534, sem root) — fallback local com aviso se Docker offline
- `terminal` → whitelist de comandos permitidos
- `http_request` → SSRF bloqueado (IPs privados bloqueados)
- `read_file` → whitelist de pastas configurável
- `browser` → headless Chromium, screenshot analisado por VLM local

```bash
# Buildar sandbox com numpy/pandas/matplotlib/scipy
build_sandbox.bat
```

---

## 🚀 Instalação

### Pré-requisitos
- [Ollama](https://ollama.com) instalado e rodando
- Python 3.10+
- Node.js 18+
- Docker Desktop (para sandbox do `run_python`)

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
# Rápido (2GB) — recomendado para GPUs com 4-6GB VRAM
ollama pull llama3.2:3b

# Mais capaz (4.7GB)
ollama pull qwen2.5:7b

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
OLLAMA_MODEL = "llama3.2:3b"   # modelo escolhido
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
OLLAMA_MODEL      = "llama3.2:3b"    # qualquer modelo Ollama
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

# Human-in-the-Loop
HITL_ENABLED         = False
HITL_BEFORE_TOOLS    = ["email", "write_file", "terminal"]

# Especialistas com modelos diferentes
SPECIALIST_MODELS = {
    # "codigo": "qwen2.5-coder:7b",
}

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

---

## 🔒 Segurança e Privacidade

- **Zero dados externos** — nenhuma chamada para OpenAI, Anthropic ou qualquer API de IA
- **Docker sandbox** — `run_python` executa em container isolado sem acesso à rede ou filesystem
- **Whitelist de comandos** — `terminal` só executa comandos explicitamente permitidos
- **SSRF protection** — `http_request` bloqueia IPs privados (127.x, 192.168.x, 10.x)
- **Whitelist de pastas** — `read_file` e `list_directory` só acessam pastas configuradas
- **Audit log** — toda chamada de ferramenta é gravada em SQLite (`workspace/audit.db`)
- **Rate limiting** — 60 req/min por IP
- **JWT opcional** — ative com `AUTH_PASSWORD` em `config.py`

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
                     27 tools (plugins)
                            │
               memory.py  rag.py  user_profile.py
               ChromaDB   BM25    audit.db
```

---

## 📁 Estrutura do projeto

```
agente-ia-local/
├── api.py               # FastAPI + WebSocket + todos endpoints
├── agent.py             # ReActAgent + auto-correção
├── orchestrator.py      # Multi-agente (6 especialistas)
├── llm.py               # Cliente Ollama (streaming, TPS/TTFT tracking)
├── rag.py               # ChromaDB + BM25 híbrido (PDF/TXT/MD/DOCX)
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
├── tools/               # 27 ferramentas — adicione arquivos aqui
└── frontend/            # Next.js 16 + React 19 + TypeScript + Tailwind v4
```

---

## 📦 Requirements

```
# requirements.txt
requests
duckduckgo-search
fastapi
uvicorn[standard]
beautifulsoup4
python-multipart
chromadb
pypdf
rank-bm25
python-docx
watchdog
faster-whisper
pyttsx3
pyautogui
Pillow
pyperclip
playwright
PyJWT
google-api-python-client
google-auth-oauthlib
google-auth-httplib2
matplotlib
pandas
openpyxl
```

---

## 🗺️ Roadmap

### v1.0 — Entregue ✅
- [x] Tiered Memory (Redis + ChromaDB + Knowledge Graph)
- [x] Reflection Loop (critic LLM, score 1-5, retry automático)
- [x] Multi-model por especialista (troca sem restart)
- [x] Docker Sandbox para `run_python` (isolamento total)
- [x] Visual Browser (Playwright + VLM, screenshots inline no chat)
- [x] NOC Dashboard — React Flow thought tree
- [x] Human-in-the-Loop (pausa agente, usuário aprova/rejeita)

### v1.1 — Próxima
- [ ] Geração de imagens — Stable Diffusion via API local
- [ ] Exibir imagens geradas inline no chat (além de screenshots)
- [ ] Export de conversa para Markdown/Obsidian
- [ ] Auto-detect nível técnico do usuário por padrões de conversa

### Futuro
- [ ] LanceDB — substituir ChromaDB (mais rápido, serverless)
- [ ] WhatsApp Business API
- [ ] WASM sandbox (alternativa ao Docker — boot instantâneo)
- [ ] Plugin marketplace (instalar tools por URL)

---

## 🙋 FAQ

**Precisa de GPU?**
Não obrigatório, mas recomendado. Com CPU funciona — só mais lento. `llama3.2:3b` roda ok em CPU moderna.

**Funciona no Mac/Linux?**
Backend sim. Os `.bat` são Windows — no Mac/Linux use os comandos diretos do Python/npm.

**Qual modelo usar?**
- `llama3.2:3b` — mais rápido, bom para tarefas simples (2GB VRAM)
- `qwen2.5:7b` — melhor qualidade geral (4.7GB VRAM)
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
