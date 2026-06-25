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

## Funcionalidades

### Interface
- Chat estilo Claude/ChatGPT — dark mode, sidebar com histórico agrupado por data
- Streaming token a token com cursor animado
- ThinkingSteps collapsível (Raciocínio → Ação → Resultado)
- Upload de arquivos, copiar resposta, regenerar, feedback 👍👎
- Modo voz: fala para o agente (STT) e ouça a resposta (TTS)
- Dashboard de saúde do sistema (modelos, memória, uptime)

### Perfil de usuário
Salva seu nível técnico e tom preferido — o agente adapta as respostas automaticamente.

### Especialistas
O agente troca de modo conforme a tarefa:
- **Professor** — tutor adaptativo com quizzes e exercícios
- **Pesquisador** — síntese de informações e fatos verificados
- **Engenheiro** — código limpo, revisão, debugging
- **Analista de dados** — CSV, Excel, gráficos, insights

### Agendamento
Execute tarefas recorrentes via `SCHEDULED_TASKS` em `config.py`.

## Como rodar

**Pré-requisitos:** [Ollama](https://ollama.com) instalado e rodando + Node.js 18+ + Python 3

```powershell
# 1. Baixar o modelo (primeira vez)
ollama pull qwen2.5:7b

# 2. Instalar dependências Python
pip install -r requirements.txt

# 3. Instalar dependências do frontend
cd frontend && npm install && cd ..

# 4. Iniciar tudo
.\iniciar_frontend.bat
```

Abrir: `http://localhost:3000`

**Alternativa (UI HTML simples):**
```powershell
.\iniciar.bat
# Abrir: http://localhost:8000
```

## 26 Ferramentas

O agente decide sozinho qual usar. Organizadas por categoria:

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
| `keyboard` | Digita texto, atalhos |
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
                       memory.py
                       user_profile.py
```

**ReAct** (tarefas simples):
```
Task → Thought → Action → Observation → ... → Answer
```

**Plan-then-Execute** (tarefas compostas):
```
Task → Plano N passos → [executa 1 → 2 → ... → N] → Resultado
```

## Estrutura

```
IA/
├── api.py              # FastAPI + WebSocket
├── agent.py            # ReActAgent + Master System Prompt
├── orchestrator.py     # Plan-then-Execute
├── llm.py              # Cliente Ollama com streaming
├── memory.py           # Persistência de sessões
├── user_profile.py     # Perfil do usuário (nível, tom)
├── tool_loader.py      # Plugin system — carrega tools/ automaticamente
├── scheduler.py        # Tarefas agendadas
├── voice.py            # STT (faster-whisper) + TTS (pyttsx3)
├── rag.py              # Busca semântica em documentos
├── auth.py             # Autenticação
├── audit.py            # Logs de auditoria
├── config.py           # Configuração central
├── watcher.py          # Hot-reload de ferramentas
├── requirements.txt
├── docker-compose.yml
├── iniciar.bat         # Inicia backend (porta 8000)
├── iniciar_frontend.bat # Inicia backend + Next.js (8000 + 3000)
├── tools/              # 26 ferramentas (uma por arquivo)
│   ├── web_search_tool.py
│   ├── run_python_tool.py
│   └── ...
├── frontend/           # Next.js 16
│   ├── src/app/
│   ├── src/components/
│   └── src/store/
└── static/             # UI HTML legada
```

## Configuração

Tudo em `config.py` — modelo, paths, auth, scheduler, email, integrações.

```python
# Trocar modelo
OLLAMA_MODEL = "qwen2.5:7b"  # ou llama3.2, mistral, etc.

# Tarefas agendadas
SCHEDULED_TASKS = [
    {"cron": "0 8 * * *", "task": "resuma as notícias de tecnologia de hoje"},
]
```

## Adicionar nova ferramenta

1. Criar `tools/minha_tool.py` seguindo o padrão:

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

2. Reiniciar — o plugin system carrega automaticamente.

## Dependências

```powershell
pip install requests ddgs fastapi "uvicorn[standard]" beautifulsoup4 python-multipart
pip install faster-whisper pyttsx3 pyautogui Pillow pyperclip playwright
playwright install chromium
```

## Roadmap

- [ ] Sandbox Docker para `run_python` (segurança)
- [ ] Google Drive integration
- [ ] Geração de imagens (Stable Diffusion local)
- [ ] Auto-detect nível do usuário pelo padrão de conversa
- [ ] WhatsApp Business API

## Licença

MIT
