"""Exposição Prometheus do roadmap "Grafana + Prometheus lendo tracing.py em
vez de só endpoint REST" — reaproveita o mesmo dict que /metrics (JSON) já
monta, só reformata pro texto que o Prometheus sabe fazer scrape."""
from metrics_prometheus import render_metrics


SAMPLE = {
    "inference": {"tps": 21.3, "ttft_ms": 340, "context_pct": 12.5,
                   "prompt_tokens": 512, "completion_tokens": 128},
    "tools": [
        {"tool": "web_search", "calls": 10, "errors": 1, "success_rate": 90.0, "avg_ms": 820},
        {"tool": "get_crypto", "calls": 5, "errors": 0, "success_rate": 100.0, "avg_ms": 210},
    ],
    "llm_calls": [
        {"model": "qwen2.5:7b-instruct-q3_K_M", "calls": 30, "errors": 1, "fallbacks": 0,
         "avg_ms": 4200, "avg_tps": 19.8, "error_rate": 3.3},
    ],
    "reflection": {"total": 12, "rewrites": 3, "rewrite_rate": 25.0, "avg_score": 3.8},
    "circuit_breaker": [
        {"tool": "slack", "failures": 5, "open": True, "cooldown_remaining_s": 120.0},
    ],
    "knowledge_graph": {"entities": 42, "relations": 87},
    "vram": {"used_mb": 3200, "total_mb": 6144, "free_mb": 2944, "pct": 52.1},
}


def test_render_includes_help_and_type_once_per_metric():
    text = render_metrics(SAMPLE)

    assert text.count("# TYPE ia_tool_calls gauge") == 1  # 2 tools, mas HELP/TYPE só 1x
    assert 'ia_tool_calls{tool="web_search"} 10' in text
    assert 'ia_tool_calls{tool="get_crypto"} 5' in text


def test_render_includes_llm_model_labels():
    text = render_metrics(SAMPLE)

    assert 'ia_llm_avg_tps{model="qwen2.5:7b-instruct-q3_K_M"} 19.8' in text
    assert 'ia_llm_error_rate_percent{model="qwen2.5:7b-instruct-q3_K_M"} 3.3' in text


def test_render_scalar_metrics_without_labels():
    text = render_metrics(SAMPLE)

    assert "ia_reflection_rewrite_rate_percent 25.0" in text
    assert "ia_vram_pct 52.1" in text
    assert "ia_kg_entities 42" in text


def test_render_circuit_breaker_open_as_zero_or_one():
    text = render_metrics(SAMPLE)

    assert 'ia_circuit_breaker_open{tool="slack"} 1' in text


def test_render_skips_missing_data_without_crashing():
    empty: dict = {"inference": {}, "tools": [], "llm_calls": [], "reflection": {},
              "circuit_breaker": [], "knowledge_graph": {}, "vram": {}}

    text = render_metrics(empty)

    assert text.strip() == ""  # nada pra expor -- sem crash, sem linha lixo


def test_render_escapes_quotes_in_label_values():
    weird = dict(SAMPLE)
    weird["tools"] = [{"tool": 'tool"with"quotes', "calls": 1, "errors": 0,
                        "success_rate": 100.0, "avg_ms": 5}]

    text = render_metrics(weird)

    assert 'tool="tool\\"with\\"quotes"' in text
