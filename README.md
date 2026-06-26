# 🤖 Agente IA Local

> Assistente de IA autônomo rodando **100% na sua máquina** — sem APIs externas, sem custos por token, sem dados saindo do seu PC.

Usa Ollama para inferência local, arquitetura ReAct para raciocínio passo a passo, e 27 ferramentas reais para executar tarefas complexas.

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
- **VRAM** — barra de uso de memória da GPU
- **Taxa de sucesso por ferramenta** — últimos 7 dias

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
- `run_python` → Docker isolado (sem rede, 128MB RAM, 0.5 CPU, read-only FS)
- `terminal` → whitelist de comandos permitidos
- `http_request` → SSRF bloqueado (IPs privados bloqueados)
- `read_file` → whitelist de pastas configurável

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

# Para análise de imagens
ollama pull llava:7b
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
# Modelo
OLLAMA_MODEL      = "llama3.2:3b"   # qualquer modelo Ollama
VISION_MODEL      = "llava:7b"      # para analyze_image

# Performance
NUM_PREDICT       = 400             # max tokens por step
NUM_CTX           = 3072            # context window
TEMPERATURE       = 0.1

# Limites de segurança
TOOL_TIMEOUT      = 30              # segundos por ferramenta
MAX_TOOL_CALLS    = 25              # chamadas por tarefa
MAX_TOOL_RETRIES  = 3               # tentativas de auto-correção
TASK_TIMEOUT      = 300             # timeout total da tarefa

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

### v0.5 — próxima
- [ ] DAG Workflow Visualization — grafo interativo da execução (React Flow)
- [ ] Embeddings locais — `nomic-embed-text` via Ollama para melhor busca em português
- [ ] Geração de imagens — Stable Diffusion via Automatic1111 API
- [ ] Exibir imagens/gráficos gerados diretamente no chat

### Futuro
- [ ] LanceDB — substituir ChromaDB (mais rápido, serverless)
- [ ] Auto-detect nível do usuário por padrões de conversa
- [ ] Export de conversa para Markdown/Obsidian
- [ ] WhatsApp Business API
- [ ] WASM sandbox (alternativa ao Docker — inicialização instantânea)
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
