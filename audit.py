import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta

AUDIT_DB = os.path.join(os.path.dirname(__file__), "workspace", "audit.db")
log      = logging.getLogger(__name__)


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(AUDIT_DB), exist_ok=True)
    c = sqlite3.connect(AUDIT_DB)
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT    NOT NULL,
            tool      TEXT    NOT NULL,
            input     TEXT,
            output    TEXT,
            duration  REAL,
            ip        TEXT
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_ts   ON audit_log(ts)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tool ON audit_log(tool)")
    c.commit()
    return c


def log_action(tool: str, input_data, output: str, duration: float = 0.0, ip: str = ""):
    # "with conn:" só faz commit/rollback (semântica do sqlite3), NÃO fecha a
    # conexão — sem close() explícito, cada chamada vaza um fd até o GC passar.
    c = _conn()
    try:
        inp = json.dumps(input_data, ensure_ascii=False) if not isinstance(input_data, str) else input_data
        with c:
            c.execute(
                "INSERT INTO audit_log (ts, tool, input, output, duration, ip) VALUES (?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), tool, inp[:500], output[:500], round(duration, 3), ip)
            )
    except Exception as e:
        log.warning("audit.log_action: %s", e)
    finally:
        c.close()


def tool_stats(days: int = 7) -> list[dict]:
    """Retorna taxa de sucesso por ferramenta nos últimos N dias."""
    c = _conn()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = c.execute(
            "SELECT tool, output, duration FROM audit_log WHERE ts > ?", (cutoff,)
        ).fetchall()
        stats: dict[str, dict] = {}
        for tool, output, duration in rows:
            if tool not in stats:
                stats[tool] = {"tool": tool, "calls": 0, "errors": 0, "total_ms": 0.0}
            stats[tool]["calls"]    += 1
            stats[tool]["total_ms"] += (duration or 0) * 1000
            out = (output or "").strip()
            if out.startswith("Erro:") or out.startswith("Bloqueado:") or "Traceback" in out[:80]:
                stats[tool]["errors"] += 1
        result = []
        for s in stats.values():
            calls  = s["calls"]
            errors = s["errors"]
            s["success_rate"] = round((calls - errors) / calls * 100, 1) if calls > 0 else 100.0
            s["avg_ms"]       = round(s["total_ms"] / calls, 0) if calls > 0 else 0
            del s["total_ms"]
            result.append(s)
        return sorted(result, key=lambda x: x["calls"], reverse=True)
    except Exception:
        return []
    finally:
        c.close()


def prune(max_age_days: int = 30) -> dict:
    """Remove entradas mais velhas que max_age_days — sem isso audit_log cresce
    pra sempre. Manual/sob-demanda (igual knowledge_graph.consolidate), não
    automático: scheduler.py só roda agent.run(task), não é o lugar certo pra
    manutenção interna."""
    cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
    c = _conn()
    try:
        before = c.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        c.execute("DELETE FROM audit_log WHERE ts < ?", (cutoff,))
        c.commit()
        c.execute("VACUUM")
        after = c.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        return {"removed": before - after, "remaining": after}
    except Exception as e:
        log.warning("audit.prune: %s", e)
        return {"removed": 0, "remaining": 0, "error": str(e)}
    finally:
        c.close()


def query(limit: int = 100, tool_filter: str = "") -> list[dict]:
    c = _conn()
    try:
        if tool_filter:
            rows = c.execute(
                "SELECT ts,tool,input,output,duration,ip FROM audit_log WHERE tool=? ORDER BY id DESC LIMIT ?",
                (tool_filter, limit)
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT ts,tool,input,output,duration,ip FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [{"ts": r[0], "tool": r[1], "input": r[2], "output": r[3], "duration": r[4], "ip": r[5]} for r in rows]
    except Exception:
        return []
    finally:
        c.close()
