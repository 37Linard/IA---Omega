"""
Copie este arquivo para config.py e ajuste as configurações.
    cp config.example.py config.py
"""
import os

_HOME    = os.path.expanduser("~")
_PROJECT = os.path.dirname(os.path.abspath(__file__))

# ── Modelo Ollama ──────────────────────────────────────────────────────────
# Liste os modelos instalados: ollama list
# Baixe novos: ollama pull qwen2.5:7b-instruct-q3_K_M
#
# Em GPU de 6GB (ex.: RTX 2060), qwen2.5:7b no quant padrão (Q4_K_M, 4.68GB) NÃO
# cabe inteiro na VRAM — roda parte na CPU e fica bem mais lento. O quant Q3_K_M
# (3.81GB) cabe 100% e passou nas mesmas golden tasks (eval_harness.py) do Q4_K_M,
# validado em 2026-07-22. Se sua GPU tem mais VRAM sobrando, pode usar "qwen2.5:7b"
# (Q4_K_M) direto para mais qualidade. llama3.2:3b é mais rápido ainda mas ignora
# instrução/repete tool call às vezes — não recomendado como modelo principal.
#
# Ganho extra de performance (sem trocar modelo): setar as env vars do Ollama
#   OLLAMA_FLASH_ATTENTION=1  e  OLLAMA_KV_CACHE_TYPE=q8_0
# antes de iniciar o serviço Ollama — reduz uso de VRAM e acelera geração (~30-40%
# medido). Precisa reiniciar o app do Ollama depois de setar (setx + relançar).
OLLAMA_MODEL   = "qwen2.5:7b-instruct-q3_K_M"
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
KEEP_ALIVE        = "30m"  # Ollama descarrega modelo após 5min ocioso por padrão — evita recarregar 7B a cada pausa

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
IMAGE_GEN_UNLOAD_OLLAMA  = True     # descarrega Ollama da VRAM antes de gerar na GPU (GPUs pequenas
                                     # não cabem os dois juntos). Ollama recarrega sozinho no próximo
                                     # request normal (KEEP_ALIVE), só adiciona latência nesse 1º request.

# -- Plugin marketplace (opcional, desligado por padrao) --------------------
# Ver plugin_manager.py pro modelo de seguranca antes de habilitar.
PLUGINS_ENABLED = False

# ── Human-in-the-Loop — permissão em camadas por risco (opcional) ──────────
# read: só lê. write: muda estado local (reversível). destructive: efeito
# externo/visível a terceiros ou controle real de OS/browser.
TOOL_RISK_TIERS: dict = {
    "fetch_page": "read", "web_search": "read", "rag_search": "read",
    "read_file": "read", "list_directory": "read", "read_spreadsheet": "read",
    "get_currency": "read", "get_crypto": "read", "analyze_image": "read",
    "screenshot": "read", "echo": "read", "clipboard": "read",

    "write_file": "write", "save_note": "write", "generate_chart": "write",
    "generate_image": "write", "generate_report": "write", "run_python": "write",
    "run_sql": "write", "remember_fact": "write", "http_request": "write",

    "send_email": "destructive", "terminal": "destructive", "git": "destructive",
    "browser": "destructive", "google_drive": "destructive", "notion": "destructive",
    "slack": "destructive", "discord_notify": "destructive",
    "keyboard": "destructive", "mouse": "destructive",
}
DEFAULT_TOOL_RISK = "write"          # tool nova/não listada — cautela por padrão
HITL_ENABLED       = False           # pausa agente e pede aprovação humana
HITL_GATE_TIERS    = ["destructive"]  # quais tiers disparam HITL quando HITL_ENABLED=True

# keyboard/mouse não têm whitelist possível (controle bruto de tecla/clique) —
# única defesa real é aprovação humana, trava sempre mesmo com HITL_ENABLED=False.
ALWAYS_HITL_TOOLS  = {"keyboard", "mouse"}
