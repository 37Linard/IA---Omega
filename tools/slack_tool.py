import logging

log = logging.getLogger(__name__)


def _get_config():
    try:
        from config import SLACK_WEBHOOK_URL, SLACK_BOT_TOKEN
        return SLACK_WEBHOOK_URL, SLACK_BOT_TOKEN
    except ImportError:
        return "", ""


class SlackTool:
    name = "slack"
    description = (
        "Envia mensagem no Slack. "
        "Input: {'message': 'texto', 'channel': '#canal', 'action': 'send|list_channels'}"
    )

    def run(self, input_data: dict) -> str:
        webhook_url, bot_token = _get_config()
        action = input_data.get("action", "send").lower()

        if action == "send":
            message = input_data.get("message", "").strip()
            if not message:
                return "Erro: 'message' obrigatório."

            # Webhook mode (simpler)
            if webhook_url:
                return self._send_webhook(webhook_url, message, input_data)

            # Bot token mode
            if bot_token:
                return self._send_bot(bot_token, message, input_data)

            return (
                "Slack não configurado. Adicione em config.py:\n"
                "- SLACK_WEBHOOK_URL (mais simples): slack.com/apps/incoming-webhooks\n"
                "- SLACK_BOT_TOKEN: api.slack.com/apps → OAuth tokens"
            )

        return f"Ação desconhecida: '{action}'. Use 'send'."

    def _send_webhook(self, url: str, message: str, input_data: dict) -> str:
        try:
            import requests
        except ImportError:
            return "Erro: requests não instalado."

        channel = input_data.get("channel", "")
        payload = {"text": message}
        if channel:
            payload["channel"] = channel

        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200 and r.text == "ok":
            return f"Mensagem enviada no Slack com sucesso."
        return f"Erro Slack ({r.status_code}): {r.text[:200]}"

    def _send_bot(self, token: str, message: str, input_data: dict) -> str:
        try:
            import requests
        except ImportError:
            return "Erro: requests não instalado."

        channel = input_data.get("channel", "#general")
        r = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": channel, "text": message},
            timeout=10,
        )
        data = r.json()
        if data.get("ok"):
            return f"Mensagem enviada no canal {channel} do Slack."
        return f"Erro Slack: {data.get('error', 'desconhecido')}"
