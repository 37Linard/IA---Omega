import json
import logging
import os
import sqlite3
from datetime import datetime

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
    try:
        inp = json.dumps(input_data, ensure_ascii=False) if not isinstance(input_data, str) else input_data
        with _conn() as c:
            c.execute(
                "INSERT INTO audit_log (ts, tool, input, output, duration, ip) VALUES (?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), tool, inp[:500], output[:500], round(duration, 3), ip)
            )
    except Exception as e:
        log.warning("audit.log_action: %s", e)


def query(limit: int = 100, tool_filter: str = "") -> list[dict]:
    try:
        with _conn() as c:
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
