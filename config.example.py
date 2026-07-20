"""
Copie este arquivo para config.py e ajuste as configurações.
    cp config.example.py config.py
"""
import os

_HOME    = os.path.expanduser("~")
_PROJECT = os.path.dirname(os.path.abspath(__file__))

# ── Modelo Ollama ──────────────────────────────────────────────────────────
# Liste os modelos instalados: ollama list
# Baixe novos: ollama pull llama3.2:3b
OLLAMA_MODEL   = "llama3.2:3b"   # recomendado para GPUs 4-6GB VRAM
VISION_MODEL   = "llava:7b"      # usado por analyze_image (baixe com: ollama pull llava:7b)
OLLAMA_URL     = "http://localhost:11434"
FALLBACK_MODEL = ""  # modelo leve pra usar se OLLAMA_MODEL travar/timeout; "" desliga fallback

# ── Obsidian (opcional) ────────────────────────────────────────────────────
OBSIDIAN_BASE  = os.path.join(_HOME, "Documents", "Obsidian Vault")
# Ou defina via variável de ambiente: OBSIDIAN_BASE=/caminho/do/vault

# ── Agente ────────────────────────────────────────────────────────────────
MAX_STEPS         = 10
NUM_PREDICT       = 400    # max tokens por step (400 = rápido, 800 = mais detalhado)
NUM_CTX           = 3072   # context window (3072 = padrão, 4096 = mais contexto)
NUM_GPU           = -1     # -1 = usa todas as camadas GPU disponíveis
TEMPERATURE       = 0.1    # 0.0 = determinístico, 1.0 = criativo

TOOL_TIMEOUT      = 30     # segundos máximos por ferramenta (padrão)
TOOL_TIMEOUTS: dict = {    # overrides por ferramenta — usa TOOL_TIMEOUT se não listada aqui
    "generate_image": 180,  # Stable Diffusion local — CPU é lento, GPU carrega modelo na 1ª chamada
}
MAX_TOOL_CALLS    = 25     # max chamadas de ferramenta por tarefa
MAX_TOOL_RETRIES  = 3      # tentativas de auto-correção em caso de erro
TASK_TIMEOUT      = 300    # timeout total da tarefa em segundos

# ── Autenticação ──────────────────────────────────────────────────────────
AUTH_PASSWORD    = ""      # vazio = sem senha; preencha para proteger o acesso
JWT_SECRET       = os.environ.get("JWT_SECRET", "")
JWT_EXPIRE_HOURS = 24

# ── Rate limiting ─────────────────────────────────────────────────────────
RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW   = 60

# ── Tarefas agendadas ─────────────────────────────────────────────────────
SCHEDULED_TASKS = [
    # {"label": "Notícias", "task": "pesquise notícias de tech hoje", "hour": 8, "minute": 0},
]

# ── Email (opcional) ──────────────────────────────────────────────────────
SMTP_HOST      = ""   # ex: smtp.gmail.com
SMTP_PORT      = 587
SMTP_USER      = ""   # seu email
SMTP_PASSWORD  = ""   # senha de app (não sua senha normal)
EMAIL_FROM     = ""

# ── Pastas que o agente pode ler ──────────────────────────────────────────
ALLOWED_READ_DIRS = [
    os.path.join(_HOME, "Desktop"),
    os.path.join(_HOME, "Documents"),
    os.path.join(_HOME, "Downloads"),
    os.path.join(_PROJECT, "workspace"),
]

# ── Notion (opcional) ─────────────────────────────────────────────────────
# notion.so/my-integrations → criar integração → Internal Integration Token
NOTION_TOKEN       = ""
NOTION_DATABASE_ID = ""

# ── Slack (opcional) ──────────────────────────────────────────────────────
# api.slack.com → Your App → Incoming Webhooks
SLACK_WEBHOOK_URL = ""
SLACK_BOT_TOKEN   = ""

# ── Discord (opcional) ────────────────────────────────────────────────────
# Server Settings → Integrations → Webhooks → New Webhook → copiar URL
DISCORD_WEBHOOK_URL = ""

# ── Google Drive (opcional) ───────────────────────────────────────────────
# 1. console.cloud.google.com → ativar Drive API + Docs API
# 2. Credenciais → OAuth 2.0 → Aplicativo de computador → baixar JSON
# 3. Salvar como gdrive_credentials.json na pasta do projeto
# O token é gerado automaticamente na primeira execução (gdrive_token.json)

# ── Geração de imagem — Stable Diffusion local (opcional) ─────────────────
# Requer: pip install torch diffusers accelerate
IMAGE_GEN_MODEL          = "stabilityai/sd-turbo"
IMAGE_GEN_DEVICE         = "auto"   # "auto" | "cuda" | "cpu"
IMAGE_GEN_STEPS          = 2
IMAGE_GEN_SIZE           = 512
IMAGE_GEN_GUIDANCE_SCALE = 0.0

# -- Plugin marketplace (opcional, desligado por padrao) --------------------
# Ver plugin_manager.py pro modelo de seguranca antes de habilitar.
PLUGINS_ENABLED = False
