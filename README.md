# Agente IA Local

Agente autônomo rodando **100% local** — sem APIs externas, sem custos por token. Usa Ollama + Qwen para raciocinar e executar tarefas reais com 26 ferramentas integradas.

> Privacidade total: todos os dados ficam na sua máquina.

## Demo

```
Você: pesquise o preço do bitcoin, gere um gráfico e salve o relatório em bitcoin.md
IA:   [Thought] Preciso buscar o preço atual, depois gerar o chart, depois salvar...
      [Action]  web_search("bitcoin price today")
      [Action]  generate_chart(data, type="line")
      [Action]  write_file("bitcoin.md", relatorio)
      Pronto! Relatório salvo com gráfico em bitcoin.md
```

## Stack

| Componente | Tecnologia |
|---|---|
| LLM | Ollama `qwen2.5:7b` (GPU local) |
| Backend | Python 3 + FastAPI + WebSocket |
| Frontend | Next.js 16 + React 19 + TypeScript + Tailwind v4 |
| Estado | Zustand v5 |
| Arquitetura | ReAct + Plan-then-Execute |
| Hardware recomendado | GPU com 4GB+ VRAM |

---

## Changelog

### v0.3 — 2026-06-25 · Master Prompt + Personalização
- **Sistema de perfil** (`user_profile.py`) — salva nome, nível técnico, tom, interesses e progresso de estudo
- **Master System Prompt** em `agent.py` — IA de próxima geração com ensino, pesquisa, código e segurança
- Perfil injetado automaticamente no system prompt do agente
- **2 especialistas novos:** professor (tutor adaptativo) e analista de dados
- **4 ferramentas novas:** `read_spreadsheet` (CSV/Excel), `generate_chart` (matplotlib), `notion`, `slack`
- Endpoints de API: `GET /profile` e `POST /profile`
- UI: botão 👤 + painel de perfil com seletor de nível técnico e tom

### v0.2 — 2026-06-25 · Robustez + Computer Use + Voz
- **80+ melhorias** de bugs, segurança e robustez
- **8 ferramentas novas:** `screenshot`, `keyboard`, `mouse`, `clipboard`, `git`, `terminal`, `browser`, `email`
- **Voz:** STT com faster-whisper + TTS com pyttsx3
- **Plugin system** (`tool_loader.py`) — nova ferramenta = criar arquivo em `tools/`, sem tocar no código principal
- **Watcher** (`watcher.py`) — hot-reload de ferramentas sem reiniciar o servidor
- **Agendador** (`scheduler.py`) — tarefas recorrentes via cron
- **RAG** (`rag.py`) — busca semântica em documentos locais
- **Autenticação** (`auth.py`) + logs de auditoria (`audit.py`)
- **Dashboard de saúde** — modelos carregados, memória, uptime
- **Backup automático** de sessões
- Markdown rendering e code blocks com syntax highlight no chat
- Frontend Next.js 16 substituindo UI HTML legada

### v0.1 — inicial · MVP
- ReAct Agent com Ollama + llama3.2:3b
- 10 ferramentas básicas (read_file, write_file, web_search, run_python, etc.)
- UI HTML/CSS/JS simples via WebSocket
- Memória de sessões em JSON

---

## Funcionalidades atuais

### Interface
- Chat estilo Claude/ChatGPT — dark mode, sidebar com histórico agrupado por data e busca
- Streaming token a token com cursor animado
- ThinkingSteps collapsível (Raciocínio → Ação → Resultado)
- Upload de arquivos, copiar resposta, regenerar, feedback 👍👎
- Modo voz: fale para o agente (STT) e ouça a resposta (TTS)
- Dashboard de saúde do sistema (modelos, memória, uptime)

### Perfil de usuário
Salva nível técnico e tom preferido — o agente adapta as respostas automaticamente.

### Especialistas
O agente troca de modo conforme a tarefa:
- **Professor** — tutor adaptativo com quizzes e exercícios
- **Pesquisador** — síntese de informações e fatos verificados
- **Engenheiro** — código limpo, revisão, debugging
- **Analista de dados** — CSV, Excel, gráficos, insights

### Agendamento
Tarefas recorrentes via `SCHEDULED_TASKS` em `config.py`.

---

## Como rodar

**Pré-requisitos:** [Ollama](https://ollama.com) + Node.js 18+ + Python 3

```powershell
# 1. Baixar o modelo (primeira vez)
ollama pull qwen2.5:7b

# 2. Dependências Python
pip install -r requirements.txt

# 3. Dependências do frontend
cd frontend && npm install && cd ..

# 4. Iniciar tudo
.\iniciar_frontend.bat
```

Abrir: `http://localhost:3000`

**Alternativa — UI HTML simples (sem Node.js):**
```powershell
.\iniciar.bat
# Abrir: http://localhost:8000
```

---

## 26 Ferramentas

O agente decide sozinho qual usar:

### Arquivos e sistema
| Ferramenta | O que faz |
|---|---|
| `read_file` | Lê qualquer arquivo |
| `write_file` | Cria ou sobrescreve arquivo |
| `list_directory` | Lista conteúdo de pasta |
| `run_python` | Executa código Python |
| `terminal` | Executa comandos no terminal |
| `git` | Operações git (status, commit, diff) |

### Web e rede
| Ferramenta | O que faz |
|---|---|
| `web_search` | Pesquisa DuckDuckGo |
| `fetch_page` | Extrai conteúdo de página web |
| `http_request` | Requisição HTTP para qualquer URL |
| `browser` | Controla browser (Playwright) |

### Dados e análise
| Ferramenta | O que faz |
|---|---|
| `run_sql` | Executa queries SQL |
| `read_spreadsheet` | Lê CSV e Excel |
| `generate_chart` | Gera gráficos (matplotlib) |
| `rag_search` | Busca semântica em documentos |
| `analyze_image` | Analisa e descreve imagens |

### Memória e notas
| Ferramenta | O que faz |
|---|---|
| `remember_fact` | Salva fato na memória do agente |
| `save_note` | Salva nota no Obsidian |

### Computer use
| Ferramenta | O que faz |
|---|---|
| `screenshot` | Captura tela |
| `keyboard` | Digita texto e atalhos |
| `mouse` | Clica, move, scroll |
| `clipboard` | Lê e escreve área de transferência |

### Integrações
| Ferramenta | O que faz |
|---|---|
| `get_currency` | Cotação de moedas em tempo real |
| `email` | Envia e-mails |
| `notion` | Cria páginas no Notion |
| `slack` | Envia mensagens no Slack |
| `echo` | Debug/teste |

---

## Arquitetura

```
Browser ──WebSocket──► FastAPI (api.py)
                            │
                    ┌───────┴────────┐
               Orchestrator      ReActAgent
               (multi-step)      (single task)
                    │                │
              ┌─────┴─────┐    LLM (llm.py)
           Planner    Executor   Ollama local
                            │
                      tool_loader.py
                      tools/ (26 plugins)
                            │
                    memory.py  user_profile.py
```

**ReAct** (tarefas simples):
```
Task → Thought → Action → Observation → ... → Answer
```

**Plan-then-Execute** (tarefas compostas):
```
Task → Plano N passos → [executa 1 → 2 → ... → N] → Resultado
```

---

## Estrutura

```
IA/
├── api.py               # FastAPI + WebSocket endpoints
├── agent.py             # ReActAgent + Master System Prompt
├── orchestrator.py      # Plan-then-Execute
├── llm.py               # Cliente Ollama com streaming
├── memory.py            # Persistência de sessões
├── user_profile.py      # Perfil do usuário (nível, tom)
├── tool_loader.py       # Plugin system automático
├── scheduler.py         # Tarefas agendadas (cron)
├── voice.py             # STT (faster-whisper) + TTS (pyttsx3)
├── rag.py               # Busca semântica em documentos
├── auth.py              # Autenticação
├── audit.py             # Logs de auditoria
├── config.py            # Configuração central
├── watcher.py           # Hot-reload de ferramentas
├── requirements.txt
├── docker-compose.yml
├── iniciar.bat          # Backend porta 8000
├── iniciar_frontend.bat # Backend 8000 + Next.js 3000
├── tools/               # 26 ferramentas (uma por arquivo)
├── frontend/            # Next.js 16
│   ├── src/app/
│   ├── src/components/
│   └── src/store/
└── static/              # UI HTML legada
```

---

## Configuração

Tudo em `config.py`:

```python
OLLAMA_MODEL = "qwen2.5:7b"  # trocar modelo aqui

SCHEDULED_TASKS = [
    {"cron": "0 8 * * *", "task": "resuma as notícias de tecnologia de hoje"},
]
```

---

## Adicionar nova ferramenta

1. Criar `tools/minha_tool.py`:

```python
def get_tool():
    return {
        "name": "minha_tool",
        "description": "O que faz",
        "parameters": {"param": {"type": "string", "description": "..."}},
        "function": executar
    }

def executar(param: str) -> str:
    return resultado
```

2. Salvar — o watcher recarrega automaticamente.

---

## Dependências

```powershell
pip install requests ddgs fastapi "uvicorn[standard]" beautifulsoup4 python-multipart
pip install faster-whisper pyttsx3 pyautogui Pillow pyperclip playwright
playwright install chromium
```

---

## Problemas conhecidos

| Problema | Status |
|---|---|
| `run_python` executa sem sandbox — código malicioso pode afetar o sistema | Aguardando Docker sandbox |
| Computer use (`mouse`, `keyboard`) pode conflitar com uso normal do PC durante execução | Em investigação |
| Voz TTS (pyttsx3) não funciona em alguns ambientes sem driver de áudio | Documentar alternativas |
| `rag_search` requer indexação prévia manual dos documentos | Melhorar UX de indexação |

---

## Roadmap

### v0.4 — próxima
- [ ] **Sandbox Docker** para `run_python` (isolamento e segurança)
- [ ] **Google Drive** — ler, criar e atualizar documentos
- [ ] Melhorar UX de indexação RAG (arrastar pasta → indexar)

### Futuro
- [ ] Geração de imagens (Stable Diffusion local)
- [ ] Auto-detect nível do usuário pelo padrão de conversa
- [ ] WhatsApp Business API
- [ ] Multi-agente paralelo (tarefas em subagentes simultâneos)
- [ ] Modo offline completo sem dependência de rede (incluindo busca local)

---

## Licença

MIT
