from datetime import datetime

import tools.schedule_task_tool as st
from scheduler import _combined_tasks, _due_now


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
