import requests
import pytest

import llm as llm_mod
from llm import OllamaLLM


def _fake_response(status_code=200, data=None):
    class FakeResponse:
        def __init__(self):
            self.status_code = status_code
            self.text = str(data)

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(f"{self.status_code} error", response=self)

        def json(self):
            return data or {}
    return FakeResponse()


def _stats_payload(text):
    return {
        "response": text,
        "eval_count": 5, "eval_duration": 1_000_000_000,
        "prompt_eval_count": 5, "prompt_eval_duration": 1_000_000,
        "load_duration": 1_000_000,
    }


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    monkeypatch.setattr(llm_mod, "RETRY_DELAY", 0)


def test_generate_succeeds_on_first_try(monkeypatch):
    calls = []

    def fake_post(url, json=None, timeout=None, **kw):
        calls.append(json["model"])
        return _fake_response(200, _stats_payload("resposta principal"))

    monkeypatch.setattr(llm_mod.requests, "post", fake_post)

    result = OllamaLLM(model="qwen2.5:7b", fallback_model="llama3.2:3b").generate("oi")

    assert result == "resposta principal"
    assert calls == ["qwen2.5:7b"]


def test_generate_falls_back_when_primary_exhausts_retries(monkeypatch):
    calls = []

    def fake_post(url, json=None, timeout=None, **kw):
        model = json["model"]
        calls.append(model)
        if model == "qwen2.5:7b":
            raise requests.exceptions.ConnectionError("simulado: fora do ar")
        return _fake_response(200, _stats_payload("resposta do fallback"))

    monkeypatch.setattr(llm_mod.requests, "post", fake_post)

    result = OllamaLLM(model="qwen2.5:7b", fallback_model="llama3.2:3b").generate("oi")

    assert result == "resposta do fallback"
    assert calls == ["qwen2.5:7b", "qwen2.5:7b", "qwen2.5:7b", "llama3.2:3b"]


def test_generate_raises_when_primary_and_fallback_both_fail(monkeypatch):
    def fake_post(url, json=None, timeout=None, **kw):
        raise requests.exceptions.ConnectionError(f"simulado: {json['model']} fora")

    monkeypatch.setattr(llm_mod.requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        OllamaLLM(model="qwen2.5:7b", fallback_model="llama3.2:3b").generate("oi")


def test_generate_without_fallback_configured_raises_after_retries(monkeypatch):
    calls = []

    def fake_post(url, json=None, timeout=None, **kw):
        calls.append(json["model"])
        raise requests.exceptions.Timeout("simulado")

    monkeypatch.setattr(llm_mod.requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        OllamaLLM(model="qwen2.5:7b", fallback_model="").generate("oi")

    assert calls == ["qwen2.5:7b", "qwen2.5:7b", "qwen2.5:7b"]


def test_generate_does_not_retry_or_fallback_on_http_error(monkeypatch):
    calls = []

    def fake_post(url, json=None, timeout=None, **kw):
        calls.append(json["model"])
        return _fake_response(404, {"error": "model not found"})

    monkeypatch.setattr(llm_mod.requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        OllamaLLM(model="qwen2.5:7b", fallback_model="llama3.2:3b").generate("oi")

    assert calls == ["qwen2.5:7b"]  # sem retry, sem fallback — erro real da API


def test_fallback_never_used_when_equal_to_primary(monkeypatch):
    calls = []

    def fake_post(url, json=None, timeout=None, **kw):
        calls.append(json["model"])
        raise requests.exceptions.Timeout("simulado")

    monkeypatch.setattr(llm_mod.requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        OllamaLLM(model="llama3.2:3b", fallback_model="llama3.2:3b").generate("oi")

    assert calls == ["llama3.2:3b", "llama3.2:3b", "llama3.2:3b"]
