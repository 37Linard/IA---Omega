import requests

import llm as llm_mod
import tracing as tracing_mod
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


def _stats_payload(text, prompt_tokens=10, completion_tokens=5):
    return {
        "response": text,
        "eval_count": completion_tokens, "eval_duration": 1_000_000_000,
        "prompt_eval_count": prompt_tokens, "prompt_eval_duration": 1_000_000,
        "load_duration": 1_000_000,
    }


def test_record_and_read_span(tmp_path, monkeypatch):
    monkeypatch.setattr(tracing_mod, "TRACE_DB", str(tmp_path / "traces.db"))

    tracing_mod.record_span(
        kind="generate", model="qwen2.5:7b", duration_ms=123.4,
        prompt_tokens=10, completion_tokens=5, tps=7.5, success=True,
        prompt_preview="oi",
    )

    rows = tracing_mod.recent(limit=10)
    assert len(rows) == 1
    assert rows[0]["model"] == "qwen2.5:7b"
    assert rows[0]["kind"] == "generate"
    assert rows[0]["success"] == 1
    assert rows[0]["prompt_tokens"] == 10


def test_stats_aggregates_per_model(tmp_path, monkeypatch):
    monkeypatch.setattr(tracing_mod, "TRACE_DB", str(tmp_path / "traces.db"))

    tracing_mod.record_span(kind="generate", model="a", duration_ms=100, tps=10, success=True)
    tracing_mod.record_span(kind="generate", model="a", duration_ms=200, tps=20, success=False, error="timeout")
    tracing_mod.record_span(kind="generate", model="b", duration_ms=50, tps=5, success=True)

    result = {r["model"]: r for r in tracing_mod.stats(days=7)}

    assert result["a"]["calls"] == 2
    assert result["a"]["errors"] == 1
    assert result["a"]["error_rate"] == 50.0
    assert result["a"]["avg_ms"] == 150.0
    assert result["b"]["calls"] == 1
    assert result["b"]["errors"] == 0


def test_stats_excludes_old_spans_outside_window(tmp_path, monkeypatch):
    monkeypatch.setattr(tracing_mod, "TRACE_DB", str(tmp_path / "traces.db"))
    from datetime import datetime, timedelta
    c = tracing_mod._conn()
    with c:
        c.execute(
            "INSERT INTO llm_spans (ts, kind, model, duration_ms, prompt_tokens, "
            "completion_tokens, tps, success, error, fallback_used, prompt_preview) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ((datetime.now() - timedelta(days=30)).isoformat(), "generate", "old-model",
             10.0, 0, 0, 0.0, 1, "", 0, ""),
        )
    c.close()

    result = tracing_mod.stats(days=1)

    assert result == []


def test_generate_records_span_on_success(tmp_path, monkeypatch):
    monkeypatch.setattr(tracing_mod, "TRACE_DB", str(tmp_path / "traces.db"))
    monkeypatch.setattr(llm_mod, "RETRY_DELAY", 0)

    def fake_post(url, json=None, timeout=None, **kw):
        return _fake_response(200, _stats_payload("resposta"))
    monkeypatch.setattr(llm_mod.requests, "post", fake_post)

    OllamaLLM(model="qwen2.5:7b", fallback_model="").generate("pergunta de teste")

    rows = tracing_mod.recent(limit=10)
    assert len(rows) == 1
    assert rows[0]["model"] == "qwen2.5:7b"
    assert rows[0]["kind"] == "generate"
    assert rows[0]["success"] == 1
    assert rows[0]["prompt_tokens"] == 10
    assert rows[0]["completion_tokens"] == 5
    assert rows[0]["fallback_used"] == 0
    assert "pergunta de teste" in rows[0]["prompt_preview"]


def test_generate_records_span_with_fallback_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(tracing_mod, "TRACE_DB", str(tmp_path / "traces.db"))
    monkeypatch.setattr(llm_mod, "RETRY_DELAY", 0)

    def fake_post(url, json=None, timeout=None, **kw):
        model = json["model"]
        if model == "qwen2.5:7b":
            raise requests.exceptions.ConnectionError("fora do ar")
        return _fake_response(200, _stats_payload("fallback ok"))
    monkeypatch.setattr(llm_mod.requests, "post", fake_post)

    OllamaLLM(model="qwen2.5:7b", fallback_model="llama3.2:3b").generate("oi")

    rows = tracing_mod.recent(limit=10)
    assert len(rows) == 1  # só span do fallback bem-sucedido é gravado (não das 3 tentativas falhas)
    assert rows[0]["model"] == "llama3.2:3b"
    assert rows[0]["fallback_used"] == 1
    assert rows[0]["success"] == 1


def test_prune_removes_only_spans_older_than_cutoff(tmp_path, monkeypatch):
    monkeypatch.setattr(tracing_mod, "TRACE_DB", str(tmp_path / "traces.db"))
    from datetime import datetime, timedelta
    c = tracing_mod._conn()
    with c:
        c.execute(
            "INSERT INTO llm_spans (ts, kind, model, duration_ms, prompt_tokens, "
            "completion_tokens, tps, success, error, fallback_used, prompt_preview) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ((datetime.now() - timedelta(days=60)).isoformat(), "generate", "old",
             10.0, 0, 0, 0.0, 1, "", 0, ""),
        )
    c.close()
    tracing_mod.record_span(kind="generate", model="new", duration_ms=10.0, success=True)

    result = tracing_mod.prune(max_age_days=30)

    assert result["removed"] == 1
    assert result["remaining"] == 1
    rows = tracing_mod.recent(limit=10)
    assert len(rows) == 1
    assert rows[0]["model"] == "new"


def test_prune_keeps_everything_when_nothing_is_old(tmp_path, monkeypatch):
    monkeypatch.setattr(tracing_mod, "TRACE_DB", str(tmp_path / "traces.db"))
    tracing_mod.record_span(kind="generate", model="a", duration_ms=10.0, success=True)
    tracing_mod.record_span(kind="generate", model="b", duration_ms=10.0, success=True)

    result = tracing_mod.prune(max_age_days=30)

    assert result["removed"] == 0
    assert result["remaining"] == 2


def test_generate_records_span_on_total_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(tracing_mod, "TRACE_DB", str(tmp_path / "traces.db"))
    monkeypatch.setattr(llm_mod, "RETRY_DELAY", 0)

    def fake_post(url, json=None, timeout=None, **kw):
        raise requests.exceptions.Timeout("simulado")
    monkeypatch.setattr(llm_mod.requests, "post", fake_post)

    import pytest
    with pytest.raises(RuntimeError):
        OllamaLLM(model="qwen2.5:7b", fallback_model="").generate("oi")

    rows = tracing_mod.recent(limit=10)
    assert len(rows) == 1
    assert rows[0]["success"] == 0
    assert "simulado" in rows[0]["error"]
