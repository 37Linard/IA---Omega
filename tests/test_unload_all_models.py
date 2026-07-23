import llm as llm_mod
from llm import unload_all_models


def _fake_get(models):
    class FakeResponse:
        def json(self):
            return {"models": [{"name": m} for m in models]}
    def get(url, timeout=None, **kw):
        return FakeResponse()
    return get


def test_unload_all_models_posts_keep_alive_zero_for_each_loaded_model(monkeypatch):
    monkeypatch.setattr(llm_mod.requests, "get", _fake_get(["qwen2.5:7b-instruct-q3_K_M", "moondream:1.8b"]))

    posted = []

    def fake_post(url, json=None, timeout=None, **kw):
        posted.append(json)
        class FakeResponse:
            pass
        return FakeResponse()

    monkeypatch.setattr(llm_mod.requests, "post", fake_post)

    unload_all_models()

    assert [p["model"] for p in posted] == ["qwen2.5:7b-instruct-q3_K_M", "moondream:1.8b"]
    assert all(p["keep_alive"] == 0 and p["prompt"] == "" for p in posted)


def test_unload_all_models_no_op_when_ollama_unreachable(monkeypatch):
    def raising_get(url, timeout=None, **kw):
        raise ConnectionError("simulado: ollama fora do ar")

    monkeypatch.setattr(llm_mod.requests, "get", raising_get)

    posted = []
    monkeypatch.setattr(llm_mod.requests, "post", lambda *a, **kw: posted.append(1))

    unload_all_models()  # não deve levantar exceção

    assert posted == []
