"""
Tracing estruturado de chamadas LLM — um span por generate()/generate_vision(),
com latência, tokens e erro, em vez de só o agregado de sessão (session_tokens
em llm.py, que é cumulativo e se perde ao trocar de instância). Tool-calls já
tinham isso via audit.py; isso cobre o lado LLM que faltava.

Não correlaciona spans numa árvore por task (trace_id) de propósito — LLM
instances são compartilhadas entre threads (specialist paralelos no modo
colaborativo), então qualquer estado por-chamada teria que viajar via retorno
de função em vez de atributo de instância pra não vazar entre threads. Uma
tabela plana com timestamp já responde "qual chamada foi lenta/travou/gastou
tokens", que é o problema real — juntar num spantree fica pra depois se
precisar.
"""
import logging
import os
import sqlite3
from datetime import datetime, timedelta

TRACE_DB = os.path.join(os.path.dirname(__file__), "workspace", "traces.db")
log = logging.getLogger(__name__)


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(TRACE_DB), exist_ok=True)
    c = sqlite3.connect(TRACE_DB)
    c.execute("""
        CREATE TABLE IF NOT EXISTS llm_spans (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            ts                 TEXT    NOT NULL,
            kind               TEXT    NOT NULL,
            model              TEXT    NOT NULL,
            duration_ms        REAL,
            prompt_tokens      INTEGER,
            completion_tokens  INTEGER,
            tps                REAL,
            success            INTEGER NOT NULL,
            error              TEXT,
            fallback_used      INTEGER NOT NULL DEFAULT 0,
            prompt_preview     TEXT
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_llm_spans_ts    ON llm_spans(ts)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_llm_spans_model ON llm_spans(model)")
    c.commit()
    return c


def record_span(
    kind: str, model: str, duration_ms: float, *,
    prompt_tokens: int = 0, completion_tokens: int = 0, tps: float = 0.0,
    success: bool = True, error: str = "", fallback_used: bool = False,
    prompt_preview: str = "",
):
    try:
        with _conn() as c:
            c.execute(
                "INSERT INTO llm_spans (ts, kind, model, duration_ms, prompt_tokens, "
                "completion_tokens, tps, success, error, fallback_used, prompt_preview) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    datetime.now().isoformat(timespec="seconds"), kind, model,
                    round(duration_ms, 1), prompt_tokens, completion_tokens, round(tps, 1),
                    int(success), error[:300], int(fallback_used), prompt_preview[:200],
                ),
            )
    except Exception as e:
        log.warning("tracing.record_span: %s", e)


def stats(days: int = 1) -> list[dict]:
    """Latência/tokens/erro agregados por modelo, últimos N dias."""
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with _conn() as c:
            rows = c.execute(
                "SELECT model, duration_ms, success, tps, fallback_used FROM llm_spans WHERE ts > ?",
                (cutoff,),
            ).fetchall()

        agg: dict[str, dict] = {}
        for model, duration_ms, success, tps, fallback_used in rows:
            d = agg.setdefault(model, {
                "model": model, "calls": 0, "errors": 0, "fallbacks": 0,
                "_total_ms": 0.0, "_total_tps": 0.0, "_tps_n": 0,
            })
            d["calls"] += 1
            d["_total_ms"] += duration_ms or 0
            if not success:
                d["errors"] += 1
            if fallback_used:
                d["fallbacks"] += 1
            if tps:
                d["_total_tps"] += tps
                d["_tps_n"] += 1

        result = []
        for d in agg.values():
            calls = d["calls"]
            d["avg_ms"]     = round(d["_total_ms"] / calls, 0) if calls else 0
            d["avg_tps"]    = round(d["_total_tps"] / d["_tps_n"], 1) if d["_tps_n"] else 0
            d["error_rate"] = round(d["errors"] / calls * 100, 1) if calls else 0
            del d["_total_ms"], d["_total_tps"], d["_tps_n"]
            result.append(d)
        return sorted(result, key=lambda x: x["calls"], reverse=True)
    except Exception:
        return []


def prune(max_age_days: int = 30) -> dict:
    """Remove spans mais velhos que max_age_days — sem isso llm_spans cresce pra
    sempre (1 linha por chamada LLM). Manual/sob-demanda, mesmo padrão de
    audit.prune/knowledge_graph.consolidate."""
    cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
    try:
        c = _conn()
        before = c.execute("SELECT COUNT(*) FROM llm_spans").fetchone()[0]
        c.execute("DELETE FROM llm_spans WHERE ts < ?", (cutoff,))
        c.commit()
        c.execute("VACUUM")
        after = c.execute("SELECT COUNT(*) FROM llm_spans").fetchone()[0]
        c.close()
        return {"removed": before - after, "remaining": after}
    except Exception as e:
        log.warning("tracing.prune: %s", e)
        return {"removed": 0, "remaining": 0, "error": str(e)}


def recent(limit: int = 50) -> list[dict]:
    try:
        with _conn() as c:
            rows = c.execute(
                "SELECT ts, kind, model, duration_ms, prompt_tokens, completion_tokens, "
                "tps, success, error, fallback_used, prompt_preview FROM llm_spans "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        cols = ["ts", "kind", "model", "duration_ms", "prompt_tokens", "completion_tokens",
                "tps", "success", "error", "fallback_used", "prompt_preview"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []
