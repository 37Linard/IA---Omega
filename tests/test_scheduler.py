import subprocess
from datetime import datetime

import tools.schedule_task_tool as st
import scheduler as scheduler_mod
from scheduler import _combined_tasks, _due_now, _run_nightly_eval, _notify_eval_failure


def test_combined_tasks_merges_static_and_dynamic(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "TASKS_FILE", str(tmp_path / "scheduled_tasks.json"))
    st._save([{"id": "dyn1", "task": "resuma notícias", "hour": 9, "minute": 0}])
    static = [{"task": "tarefa fixa", "hour": 8, "minute": 0}]

    combined = _combined_tasks(static)

    keys = [k for k, _ in combined]
    assert "static_0" in keys
    assert "dyn1" in keys


def test_combined_tasks_works_with_no_dynamic_tasks(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "TASKS_FILE", str(tmp_path / "scheduled_tasks.json"))
    static = [{"task": "tarefa fixa", "hour": 8, "minute": 0}]

    combined = _combined_tasks(static)

    assert combined == [("static_0", static[0])]


def test_due_now_matches_exact_hour_and_minute():
    now = datetime(2026, 7, 21, 9, 0)
    combined = [("t1", {"task": "x", "hour": 9, "minute": 0}), ("t2", {"task": "y", "hour": 10, "minute": 0})]

    due = _due_now(combined, now, ran_today=set())

    assert [k for k, _ in due] == ["2026-07-21_t1"]


def test_due_now_skips_already_ran_today():
    now = datetime(2026, 7, 21, 9, 0)
    combined = [("t1", {"task": "x", "hour": 9, "minute": 0})]

    due = _due_now(combined, now, ran_today={"2026-07-21_t1"})

    assert due == []


def test_due_now_runs_again_next_day():
    combined = [("t1", {"task": "x", "hour": 9, "minute": 0})]
    ran_today = {"2026-07-20_t1"}  # rodou ontem

    due = _due_now(combined, datetime(2026, 7, 21, 9, 0), ran_today)

    assert [k for k, _ in due] == ["2026-07-21_t1"]


def test_due_now_a_task_created_via_chat_fires_like_a_static_one(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "TASKS_FILE", str(tmp_path / "scheduled_tasks.json"))
    st._save([{"id": "abc123", "task": "resuma notícias", "hour": 9, "minute": 0}])

    due = _due_now(_combined_tasks([]), datetime(2026, 7, 21, 9, 0), ran_today=set())

    assert len(due) == 1
    assert due[0][1]["task"] == "resuma notícias"


# ── Eval noturno ─────────────────────────────────────────────────────────

def _fake_completed(returncode, stdout=""):
    return subprocess.CompletedProcess(args=["eval_harness.py"], returncode=returncode, stdout=stdout, stderr="")


def test_nightly_eval_runs_as_subprocess_not_inprocess(monkeypatch):
    # achado real: eval_harness._isolate_state() redireciona globais de módulo
    # (memory.MEMORY_FILE, audit.AUDIT_DB, tracing.TRACE_DB) — rodar in-process
    # corromperia estado real de usuário de verdade conversando ao mesmo tempo.
    captured = {}
    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        captured["kw"] = kw
        return _fake_completed(0, "==== 5/5 passou ====")
    monkeypatch.setattr(subprocess, "run", fake_run)

    _run_nightly_eval()

    assert "eval_harness.py" in captured["cmd"]
    # achado real ao vivo 2026-07-23: sem encoding="utf-8" explícito, Windows
    # decodifica a saída como cp1252 e quebra com UnicodeDecodeError em
    # acento/emoji (eval_harness.py imprime em utf-8).
    assert captured["kw"]["encoding"] == "utf-8"
    assert captured["kw"]["errors"] == "replace"


def test_nightly_eval_notifies_discord_on_failure(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _fake_completed(1, "FAIL — python_arithmetic"))
    notified = []
    monkeypatch.setattr(scheduler_mod, "_notify_eval_failure", lambda tail: notified.append(tail))

    _run_nightly_eval()

    assert len(notified) == 1
    assert "FAIL" in notified[0]


def test_nightly_eval_does_not_notify_on_success(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _fake_completed(0, "==== 5/5 passou ===="))
    notified = []
    monkeypatch.setattr(scheduler_mod, "_notify_eval_failure", lambda tail: notified.append(tail))

    _run_nightly_eval()

    assert notified == []


def test_nightly_eval_timeout_does_not_raise(monkeypatch):
    def fake_run(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="eval_harness.py", timeout=900)
    monkeypatch.setattr(subprocess, "run", fake_run)

    _run_nightly_eval()  # não deve levantar


def test_notify_eval_failure_missing_webhook_does_not_raise(monkeypatch):
    import tools.discord_notify_tool as dn_mod

    class _BoomTool:
        def run(self, input_data):
            raise RuntimeError("DISCORD_WEBHOOK_URL vazio")
    monkeypatch.setattr(dn_mod, "DiscordNotifyTool", _BoomTool)

    _notify_eval_failure("saida de teste")  # não deve levantar
