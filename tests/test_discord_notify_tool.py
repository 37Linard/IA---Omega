import requests

from tools.discord_notify_tool import DiscordNotifyTool


def test_returns_setup_instructions_when_webhook_not_configured(monkeypatch):
    monkeypatch.setattr("tools.discord_notify_tool._get_webhook", lambda: "")

    result = DiscordNotifyTool().run({"message": "terminei"})

    assert "não configurado" in result.lower()


def test_requires_message(monkeypatch):
    monkeypatch.setattr("tools.discord_notify_tool._get_webhook", lambda: "https://discord.com/api/webhooks/x/y")

    result = DiscordNotifyTool().run({})

    assert "obrigatório" in result.lower()


def test_sends_webhook_and_reports_success(monkeypatch):
    monkeypatch.setattr("tools.discord_notify_tool._get_webhook", lambda: "https://discord.com/api/webhooks/x/y")

    captured = {}

    class FakeResponse:
        status_code = 204
        text = ""

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)

    result = DiscordNotifyTool().run({"message": "tarefa longa terminou", "title": "Batch OK", "status": "success"})

    assert "sucesso" in result.lower()
    assert captured["json"]["embeds"][0]["title"] == "Batch OK"
    assert captured["json"]["embeds"][0]["description"] == "tarefa longa terminou"
    assert captured["json"]["embeds"][0]["color"] == 0x2ECC71


def test_reports_discord_http_error(monkeypatch):
    monkeypatch.setattr("tools.discord_notify_tool._get_webhook", lambda: "https://discord.com/api/webhooks/x/y")

    class FakeResponse:
        status_code = 400
        text = "invalid payload"

    monkeypatch.setattr(requests, "post", lambda url, json=None, timeout=None: FakeResponse())

    result = DiscordNotifyTool().run({"message": "oi"})

    assert "erro discord (400)" in result.lower()
