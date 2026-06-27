import os

_HOME    = os.path.expanduser("~")
_PROJECT = os.path.dirname(os.path.abspath(__file__))

# ── Modelo Ollama ──────────────────────────────────────────────────────────
OLLAMA_MODEL   = "llama3.2:3b"   # troque para qwen2.5:7b, mistral, deepseek, etc.
VISION_MODEL   = "moondream:1.8b"  # VLM local — cabe em 2GB VRAM (moondream:1.8b ou llava:7b)
OLLAMA_URL     = "http://localhost:11434"
API_URL        = "http://localhost:8000"  # URL base da API (usada por tools para gerar links de imagem)

# ── Obsidian (opcional) ────────────────────────────────────────────────────
# Caminho da sua vault Obsidian — usado por save_note
OBSIDIAN_BASE  = os.environ.get(
    "OBSIDIAN_BASE",
    os.path.join(_HOME, "Documents", "Obsidian Vault")
)

# ── Agente ────────────────────────────────────────────────────────────────
MAX_STEPS         = 8      # máx iterações ReAct por tarefa
NUM_PREDICT       = 700    # tokens por step (baixo → trunca → parse error → loops extras)
NUM_CTX           = 4096   # context window em tokens
NUM_GPU           = -1     # -1 = todas as camadas na GPU (auto)
TEMPERATURE       = 0.1

TOOL_TIMEOUT      = 30     # segundos máximos por ferramenta
MAX_TOOL_CALLS    = 15     # max chamadas de ferramenta por tarefa
MAX_TOOL_RETRIES  = 3      # tentativas de auto-correção em erros
TASK_TIMEOUT      = 300    # timeout total da tarefa (5 min)

# ── Autenticação ──────────────────────────────────────────────────────────
# Deixe AUTH_PASSWORD vazio para desativar proteção por senha
AUTH_PASSWORD    = ""
JWT_SECRET       = os.environ.get("JWT_SECRET", "")  # DEFINA via env var em produção
JWT_EXPIRE_HOURS = 24

# ── Rate limiting ─────────────────────────────────────────────────────────
RATE_LIMIT_REQUESTS = 60   # max requisições por IP
RATE_LIMIT_WINDOW   = 60   # janela em segundos (0 = desativado)

# ── Tarefas agendadas ─────────────────────────────────────────────────────
SCHEDULED_TASKS = [
    # Exemplo:
    # {"label": "Notícias", "task": "pesquise as notícias de tech hoje", "hour": 8, "minute": 0},
]

# ── Email (opcional) ──────────────────────────────────────────────────────
SMTP_HOST      = ""
SMTP_PORT      = 587
SMTP_USER      = ""
SMTP_PASSWORD  = ""
EMAIL_FROM     = ""

# ── Pastas que o agente pode ler ──────────────────────────────────────────
# Adicione ou remova pastas conforme necessário
ALLOWED_READ_DIRS = [
    os.path.join(_HOME, "Desktop"),
    os.path.join(_HOME, "Documents"),
    os.path.join(_HOME, "Downloads"),
    os.path.join(_PROJECT, "workspace"),
]

# ── Reflection Loop — v1.0 ────────────────────────────────────────────────
REFLECTION_ENABLED   = True   # crítico avalia própria resposta antes de entregar
REFLECTION_THRESHOLD = 2      # score mínimo (1-5) — abaixo disso reescreve (2 = só reescreve se realmente ruim)

# ── Memória Tiered — v1.0 ─────────────────────────────────────────────────
EMBED_MODEL     = "nomic-embed-text"     # embedding local via Ollama
REDIS_URL       = "redis://localhost:6379"
SHORT_TERM_TTL  = 1800   # segundos (30 min) — TTL do contexto imediato
SHORT_TERM_MSGS = 10     # máx mensagens por sessão no contexto imediato

# ── Human-in-the-Loop (v1.0) ──────────────────────────────────────────────
HITL_ENABLED      = False                                    # pausa agente e pede aprovação humana
HITL_BEFORE_TOOLS = ["email", "write_file", "terminal"]      # ferramentas que disparam HITL

# ── Specialist models (v1.0) ──────────────────────────────────────────────
# Deixe vazio ("") para herdar OLLAMA_MODEL
MANAGER_MODEL: str = ""  # modelo para roteamento/classificação — vazio = OLLAMA_MODEL
SPECIALIST_MODELS: dict = {
    # "pesquisador": "llama3.2:3b",
    # "codigo":      "qwen2.5-coder:7b",
}

# ── Notion (opcional) ─────────────────────────────────────────────────────
# notion.so/my-integrations → criar integração → Internal Integration Token
NOTION_TOKEN       = os.environ.get("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")

# ── Slack (opcional) ──────────────────────────────────────────────────────
# api.slack.com → Your App → Incoming Webhooks ou OAuth & Permissions
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
SLACK_BOT_TOKEN   = os.environ.get("SLACK_BOT_TOKEN", "")
