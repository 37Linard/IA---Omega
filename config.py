import os

# Modelo Ollama
OLLAMA_MODEL   = "qwen2.5:7b"
VISION_MODEL   = "llava:7b"
OLLAMA_URL     = "http://localhost:11434"

# Obsidian
OBSIDIAN_BASE  = r"C:\Users\User\Documents\Obsidian Vault\Gabriel"

# Agente
MAX_STEPS      = 10
NUM_PREDICT    = 600   # era 1500 — tokens suficientes, muito mais rápido
NUM_CTX        = 4096  # contexto explícito — menos VRAM, mais velocidade
NUM_GPU        = -1    # -1 = todas as camadas na GPU (auto)
TEMPERATURE    = 0.1
TOOL_TIMEOUT   = 30   # segundos máximos por execução de ferramenta
MAX_TOOL_CALLS = 25   # máximo de chamadas de ferramentas por tarefa
TASK_TIMEOUT   = 300  # segundos máximos por tarefa inteira (5 min)

# Auth — deixe AUTH_PASSWORD vazio para desativar
AUTH_PASSWORD    = ""
JWT_SECRET       = os.environ.get("JWT_SECRET", "agente-ia-local-secret-change-me")
JWT_EXPIRE_HOURS = 24

# Rate limiting — requests por IP (0 = desativado)
RATE_LIMIT_REQUESTS = 60   # max requisições
RATE_LIMIT_WINDOW   = 60   # por janela de N segundos

# Tarefas agendadas — lista de dicts com task, hour, minute, label
SCHEDULED_TASKS = [
    # {"label": "Resumo diário", "task": "pesquise as principais notícias do Brasil hoje e salve em noticias.txt", "hour": 8, "minute": 0},
]

# Email (opcional) — preencha para ativar email_tool
SMTP_HOST      = ""
SMTP_PORT      = 587
SMTP_USER      = ""
SMTP_PASSWORD  = ""
EMAIL_FROM     = ""

# Paths permitidos para read_file e list_directory
ALLOWED_READ_DIRS = [
    r"C:\Users\User\Desktop",
    r"C:\Users\User\Documents",
    r"C:\Users\User\Downloads",
    r"C:\Users\User\Desktop\MEU\IA\workspace",
]

# Notion (opcional) — preencha para ativar notion_tool
# Como obter: notion.so/my-integrations → criar integração → copiar "Internal Integration Token"
NOTION_TOKEN       = ""
NOTION_DATABASE_ID = ""  # ID do banco de dados onde criar páginas

# Slack (opcional) — preencha WEBHOOK_URL OU BOT_TOKEN
# Webhook: api.slack.com → Your App → Incoming Webhooks
# Bot token: api.slack.com → Your App → OAuth & Permissions → Bot User OAuth Token
SLACK_WEBHOOK_URL = ""
SLACK_BOT_TOKEN   = ""
