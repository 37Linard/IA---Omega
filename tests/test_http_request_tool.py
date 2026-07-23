import requests
import tools.http_request_tool as hr_mod
from tools.http_request_tool import HttpRequestTool


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def json(self):
        if self._json_data is None:
            raise ValueError("sem json")
        return self._json_data


def test_missing_url_errors():
    result = HttpRequestTool().run({})
    assert "obrigatório" in result


def test_non_http_url_errors():
    result = HttpRequestTool().run({"url": "ftp://exemplo.com"})
    assert "http" in result.lower()


def test_blocks_private_ip(monkeypatch):
    monkeypatch.setattr(hr_mod.socket, "gethostbyname", lambda host: "192.168.1.1")

    result = HttpRequestTool().run({"url": "http://intranet.local/x"})

    assert "Bloqueado" in result


def test_blocks_loopback(monkeypatch):
    monkeypatch.setattr(hr_mod.socket, "gethostbyname", lambda host: "127.0.0.1")

    result = HttpRequestTool().run({"url": "http://localhost:11434/api/tags"})

    assert "Bloqueado" in result


def test_allows_public_ip_and_returns_json(monkeypatch):
    monkeypatch.setattr(hr_mod.socket, "gethostbyname", lambda host: "93.184.216.34")
    monkeypatch.setattr(requests, "get", lambda url, headers=None, timeout=None: _FakeResponse(200, {"ok": True}))

    result = HttpRequestTool().run({"url": "https://example.com/api"})

    assert "Status: 200" in result
    assert '"ok": true' in result


def test_post_sends_json_body(monkeypatch):
    monkeypatch.setattr(hr_mod.socket, "gethostbyname", lambda host: "93.184.216.34")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["json"] = json
        return _FakeResponse(201, {"created": True})

    monkeypatch.setattr(requests, "post", fake_post)

    result = HttpRequestTool().run({"url": "https://example.com/api", "method": "POST", "body": {"x": 1}})

    assert "Status: 201" in result
    assert captured["json"] == {"x": 1}


def test_unsupported_method_errors(monkeypatch):
    monkeypatch.setattr(hr_mod.socket, "gethostbyname", lambda host: "93.184.216.34")

    result = HttpRequestTool().run({"url": "https://example.com", "method": "DELETE"})

    assert "não suportado" in result


def test_timeout_returns_clean_error(monkeypatch):
    monkeypatch.setattr(hr_mod.socket, "gethostbyname", lambda host: "93.184.216.34")

    def fake_get(*a, **kw):
        raise requests.Timeout("simulado")
    monkeypatch.setattr(requests, "get", fake_get)

    result = HttpRequestTool().run({"url": "https://example.com"})

    assert "excedeu" in result


def test_response_body_truncated_over_3000_chars(monkeypatch):
    monkeypatch.setattr(hr_mod.socket, "gethostbyname", lambda host: "93.184.216.34")
    big_text = "x" * 5000
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _FakeResponse(200, None, big_text))

    result = HttpRequestTool().run({"url": "https://example.com"})

    assert "truncada" in result
    assert len(result) < 5000
