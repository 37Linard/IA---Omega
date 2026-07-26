"""Exposição de métricas em formato Prometheus (text exposition format,
https://prometheus.io/docs/instrumenting/exposition_formats/). Reaproveita
os mesmos agregados que /metrics (JSON) já monta a partir de
tracing.py/audit.py/circuit_breaker.py pro dashboard do frontend — só troca
o formato de saída pro que o Prometheus sabe fazer scrape. Sem
prometheus_client como dependência nova (é só formatação de texto).

Todo valor aqui é GAUGE, nunca COUNTER — os agregados vêm de uma janela de
tempo (últimos N dias) consultada do zero a cada chamada, não são contadores
monotônicos acumulados ao longo da vida do processo (o que COUNTER exige no
modelo do Prometheus)."""


def _esc(v) -> str:
    return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class _Exposition:
    def __init__(self):
        self._lines = []
        self._declared = set()

    def gauge(self, name: str, value, help_text: str = "", labels: dict | None = None):
        if value is None:
            return
        if name not in self._declared:
            if help_text:
                self._lines.append(f"# HELP {name} {help_text}")
            self._lines.append(f"# TYPE {name} gauge")
            self._declared.add(name)
        label_str = ""
        if labels:
            parts = ",".join(f'{k}="{_esc(v)}"' for k, v in labels.items())
            label_str = "{" + parts + "}"
        self._lines.append(f"{name}{label_str} {value}")

    def render(self) -> str:
        return "\n".join(self._lines) + "\n"


def render_metrics(metrics: dict) -> str:
    """`metrics` é o mesmo dict que o endpoint /metrics (JSON) retorna —
    reaproveita, não recalcula nada."""
    exp = _Exposition()

    inf = metrics.get("inference", {})
    exp.gauge("ia_inference_tps", inf.get("tps"), "Tokens/segundo da última geração")
    exp.gauge("ia_inference_ttft_ms", inf.get("ttft_ms"), "Time-to-first-token em ms")
    exp.gauge("ia_inference_context_pct", inf.get("context_pct"), "Uso da janela de contexto em %")
    exp.gauge("ia_inference_prompt_tokens", inf.get("prompt_tokens"))
    exp.gauge("ia_inference_completion_tokens", inf.get("completion_tokens"))

    for t in metrics.get("tools", []):
        labels = {"tool": t.get("tool", "")}
        exp.gauge("ia_tool_calls", t.get("calls"), "Chamadas por ferramenta (janela de 7 dias)", labels)
        exp.gauge("ia_tool_errors", t.get("errors"), "Erros por ferramenta (janela de 7 dias)", labels)
        exp.gauge("ia_tool_success_rate_percent", t.get("success_rate"), "", labels)
        exp.gauge("ia_tool_avg_duration_ms", t.get("avg_ms"), "", labels)

    for m in metrics.get("llm_calls", []):
        labels = {"model": m.get("model", "")}
        exp.gauge("ia_llm_calls", m.get("calls"), "Chamadas LLM por modelo (janela de 1 dia)", labels)
        exp.gauge("ia_llm_errors", m.get("errors"), "", labels)
        exp.gauge("ia_llm_fallbacks", m.get("fallbacks"), "", labels)
        exp.gauge("ia_llm_avg_duration_ms", m.get("avg_ms"), "", labels)
        exp.gauge("ia_llm_avg_tps", m.get("avg_tps"), "", labels)
        exp.gauge("ia_llm_error_rate_percent", m.get("error_rate"), "", labels)

    refl = metrics.get("reflection", {})
    exp.gauge("ia_reflection_total", refl.get("total"), "Avaliações do critic (janela de 7 dias)")
    exp.gauge("ia_reflection_rewrites", refl.get("rewrites"))
    exp.gauge("ia_reflection_rewrite_rate_percent", refl.get("rewrite_rate"))
    exp.gauge("ia_reflection_avg_score", refl.get("avg_score"))

    for cb in metrics.get("circuit_breaker", []):
        labels = {"tool": cb.get("tool", "")}
        exp.gauge("ia_circuit_breaker_open", 1 if cb.get("open") else 0,
                   "1 se o circuit breaker está aberto pra essa tool", labels)
        exp.gauge("ia_circuit_breaker_failures", cb.get("failures"), "", labels)

    kg = metrics.get("knowledge_graph", {})
    exp.gauge("ia_kg_entities", kg.get("entities"), "Entidades no knowledge graph")
    exp.gauge("ia_kg_relations", kg.get("relations"), "Relações no knowledge graph")

    vram = metrics.get("vram", {})
    exp.gauge("ia_vram_used_mb", vram.get("used_mb"), "VRAM usada em MB (nvidia-smi)")
    exp.gauge("ia_vram_total_mb", vram.get("total_mb"))
    exp.gauge("ia_vram_free_mb", vram.get("free_mb"))
    exp.gauge("ia_vram_pct", vram.get("pct"))

    return exp.render()
