# Agente IA Local

Agente autônomo rodando **100% local** — sem APIs externas, sem custos por token. Usa Ollama + LLaMA para raciocinar e executar tarefas reais através de ferramentas.

## Stack

| Componente | Tecnologia |
|---|---|
| LLM | Ollama `llama3.2:3b` (GPU, 100% local) |
| Backend | Python 3.14 + FastAPI + WebSocket |
| Frontend | HTML / CSS / JS (sem framework) |
| Arquitetura | ReAct + Plan-then-Execute |
| Hardware | RTX 2060 4GB VRAM |

## Como rodar

**Pré-requisito:** Ollama rodando com o modelo baixado.

```powershell
# 1. Garantir que o Ollama está ativo
ollama serve

# 2. Baixar o modelo (primeira vez)
ollama pull llama3.2:3b

# 3. Iniciar o servidor
cd "C:\Users\User\Desktop\MEU\IA"
C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m uvicorn api:app --reload --port 8000
```

**Abrir no browser:** `http://localhost:8000`

## Ferramentas disponíveis

O agente decide sozinho qual ferramenta usar para cada tarefa.

| Ferramenta | O que faz |
|---|---|
| `echo` | Retorna texto literal (debug/teste) |
| `read_file` | Lê conteúdo de arquivo |
| `write_file` | Cria ou sobrescreve arquivo |
| `list_directory` | Lista arquivos de uma pasta |
| `web_search` | Pesquisa na web (DuckDuckGo) |
| `http_request` | Faz requisição HTTP para qualquer URL |
| `run_python` | Executa código Python arbitrário |
| `get_currency` | Cotação de moedas em tempo real |
| `fetch_page` | Extrai conteúdo de uma página web |
| `save_note` | Salva nota no Obsidian |

## Arquitetura

```
Browser ──WebSocket──► FastAPI (api.py)
                            │
                       ReActAgent (agent.py)
                       ┌────┴────┐
                    LLM (llm.py)  Tools (tools/)
                    Ollama API    10 ferramentas
                            │
                       Memory (memory.py)
                       agent_memory.json
```

**Fluxo ReAct** (tarefas simples):
```
Task → Thought → Action → Observation → Thought → ... → Final Answer
```

**Fluxo Plan-then-Execute** (tarefas compostas com "e salve", "e depois", etc.):
```
Task → Plano (N passos) → Executa passo 1 → passo 2 → ... → Resultado final
```

## Estrutura de arquivos

```
IA/
├── api.py          # FastAPI + WebSocket endpoints
├── agent.py        # ReActAgent — lógica principal
├── llm.py          # Cliente Ollama com streaming
├── memory.py       # Persistência de sessões (JSON)
├── main.py         # Entry point alternativo
├── agent_memory.json
├── tools/
│   ├── __init__.py
│   ├── echo_tool.py
│   ├── read_file_tool.py
│   ├── write_file_tool.py
│   ├── list_directory_tool.py
│   ├── web_search_tool.py
│   ├── http_request_tool.py
│   ├── run_python_tool.py
│   ├── get_currency_tool.py
│   ├── fetch_page_tool.py
│   └── save_note_tool.py
└── static/
    ├── index.html
    ├── style.css
    └── app.js
```

## Memória

O agente persiste as últimas **20 sessões** em `agent_memory.json`. A cada nova tarefa ele recebe contexto das 5 sessões mais recentes, permitindo referências a execuções anteriores.

## Exemplos de uso

```
# Cotação
qual é o dólar hoje?

# Arquivo
leia o arquivo C:/Users/User/Desktop/MEU/IA/teste.txt

# Código
calcule a soma dos números de 1 a 1000

# Composto (Plan-then-Execute)
pesquise o preço do bitcoin e salve em bitcoin.txt

# Web
acesse https://exemplo.com e me diz o título da página
```

## Próximos upgrades

- [ ] Trocar modelo para `qwen2.5:7b` (mais capaz, ainda cabe na VRAM)
- [ ] Ferramenta `run_sql` para consultas em banco de dados
- [ ] Exportar sessões automaticamente para o Obsidian
- [ ] Sandbox Docker para execução segura de código
