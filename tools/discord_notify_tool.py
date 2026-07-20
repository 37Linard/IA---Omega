import logging

log = logging.getLogger(__name__)


def _get_webhook():
    try:
        from config import DISCORD_WEBHOOK_URL
        return DISCORD_WEBHOOK_URL
    except ImportError:
        return ""


class DiscordNotifyTool:
    name = "discord_notify"
    description = (
        "Envia notificação no Discord via webhook. Use ao terminar uma tarefa longa "
        "(pesquisa demorada, geração de imagem, treino, batch de arquivos etc) pra avisar "
        "o usuário que terminou, mesmo ele tendo saído da tela. "
        "Input: {'message': 'texto', 'title': 'opcional', 'status': 'success|error|info'}"
    )

    def run(self, input_data: dict) -> str:
        webhook_url = _get_webhook()
        if not webhook_url:
            return (
                "Discord não configurado. Adicione DISCORD_WEBHOOK_URL em config.py — "
                "Server Settings → Integrations → Webhooks → New Webhook."
            )

        message = input_data.get("message", "").strip()
        if not message:
            return "Erro: 'message' obrigatório."

        title = input_data.get("title", "Tarefa concluída")
        status = input_data.get("status", "success").lower()
        color = {"success": 0x2ECC71, "error": 0xE74C3C, "info": 0x3498DB}.get(status, 0x2ECC71)

        try:
            import requests
        except ImportError:
            return "Erro: requests não instalado."

        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": color,
            }]
        }

        try:
            r = requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            return f"Erro ao conectar no Discord: {e}"

        if r.status_code in (200, 204):
            return "Notificação enviada no Discord com sucesso."
        return f"Erro Discord ({r.status_code}): {r.text[:200]}"
