import tools.slack_tool as slack_mod
from tools.slack_tool import SlackTool


def _fake_response(status_code=200, text="ok", json_data=None):
    class FakeResponse:
        def __init__(self):
            self.status_code = status_code
            self.text = text
        def json(self):
            return json_data or {}
    return FakeResponse()


def test_send_uses_webhook_when_configured(monkeypatch):
    monkeypatch.setattr(slack_mod, "_get_config", lambda: ("https://hooks.slack.test/x", ""))
    captured = {}

    def fake_post(url, json=None, timeout=None, **kw):
        captured["url"] = url
        captured["json"] = json
        return _fake_response(200, "ok")
    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    result = SlackTool().run({"message": "oi", "channel": "#geral"})

    assert "sucesso" in result
    assert captured["json"]["text"] == "oi"
    assert captured["json"]["channel"] == "#geral"


def test_send_without_message_errors(monkeypatch):
    monkeypatch.setattr(slack_mod, "_get_config", lambda: ("https://hooks.slack.test/x", ""))

    result = SlackTool().run({})

    assert "obrigatório" in result


def test_send_falls_back_to_bot_token_when_no_webhook(monkeypatch):
    monkeypatch.setattr(slack_mod, "_get_config", lambda: ("", "xoxb-token"))
    import requests

    def fake_post(url, json=None, headers=None, timeout=None, **kw):
        assert "chat.postMessage" in url
        assert headers["Authorization"] == "Bearer xoxb-token"
        return _fake_response(200, json_data={"ok": True})
    monkeypatch.setattr(requests, "post", fake_post)

    result = SlackTool().run({"message": "oi"})

    assert "enviada" in result


def test_not_configured_returns_setup_instructions(monkeypatch):
    monkeypatch.setattr(slack_mod, "_get_config", lambda: ("", ""))

    result = SlackTool().run({"message": "oi"})

    assert "não configurado" in result.lower()


def test_list_channels_requires_bot_token(monkeypatch):
    monkeypatch.setattr(slack_mod, "_get_config", lambda: ("https://hooks.slack.test/x", ""))

    result = SlackTool().run({"action": "list_channels"})

    assert "SLACK_BOT_TOKEN" in result


def test_list_channels_returns_formatted_list(monkeypatch):
    monkeypatch.setattr(slack_mod, "_get_config", lambda: ("", "xoxb-token"))
    import requests

    def fake_get(url, headers=None, params=None, timeout=None, **kw):
        assert "conversations.list" in url
        return _fake_response(200, json_data={
            "ok": True,
            "channels": [
                {"name": "geral", "is_private": False},
                {"name": "secreto", "is_private": True},
            ],
        })
    monkeypatch.setattr(requests, "get", fake_get)

    result = SlackTool().run({"action": "list_channels"})

    assert "#geral (público)" in result
    assert "#secreto (privado)" in result


def test_list_channels_handles_api_error(monkeypatch):
    monkeypatch.setattr(slack_mod, "_get_config", lambda: ("", "xoxb-token"))
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _fake_response(200, json_data={"ok": False, "error": "invalid_auth"}))

    result = SlackTool().run({"action": "list_channels"})

    assert "invalid_auth" in result


def test_unknown_action_lists_valid_options(monkeypatch):
    monkeypatch.setattr(slack_mod, "_get_config", lambda: ("https://hooks.slack.test/x", ""))

    result = SlackTool().run({"action": "delete_everything"})

    assert "send" in result and "list_channels" in result
