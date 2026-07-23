import audit as audit_mod


def test_log_action_and_query_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_mod, "AUDIT_DB", str(tmp_path / "audit.db"))

    audit_mod.log_action("write_file", {"filename": "x.txt"}, "Arquivo criado", duration=0.5, ip="127.0.0.1")

    rows = audit_mod.query(limit=10)
    assert len(rows) == 1
    assert rows[0]["tool"] == "write_file"
    assert rows[0]["output"] == "Arquivo criado"


def test_prune_removes_only_entries_older_than_cutoff(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_mod, "AUDIT_DB", str(tmp_path / "audit.db"))
    from datetime import datetime, timedelta
    with audit_mod._conn() as c:
        c.execute(
            "INSERT INTO audit_log (ts, tool, input, output, duration, ip) VALUES (?,?,?,?,?,?)",
            ((datetime.now() - timedelta(days=60)).isoformat(), "old_tool", "{}", "ok", 0.1, ""),
        )
    audit_mod.log_action("new_tool", {}, "ok")

    result = audit_mod.prune(max_age_days=30)

    assert result["removed"] == 1
    assert result["remaining"] == 1
    rows = audit_mod.query(limit=10)
    assert len(rows) == 1
    assert rows[0]["tool"] == "new_tool"


def test_prune_keeps_everything_when_nothing_is_old(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_mod, "AUDIT_DB", str(tmp_path / "audit.db"))
    audit_mod.log_action("a", {}, "ok")
    audit_mod.log_action("b", {}, "ok")

    result = audit_mod.prune(max_age_days=30)

    assert result["removed"] == 0
    assert result["remaining"] == 2
