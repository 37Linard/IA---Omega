import json
import os
import time

import plan_store


def test_save_creates_running_plan_on_disk():
    pid = plan_store.new_id()
    plan_store.save(pid, "pesquisa X e salva Y", ["passo 1", "passo 2"], {"tarefa_original": "x"})

    with open(plan_store._path(pid), "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "running"
    assert data["steps"] == ["passo 1", "passo 2"]
    assert data["current_index"] == 0


def test_find_incomplete_returns_running_plan():
    pid = plan_store.new_id()
    plan_store.save(pid, "tarefa", ["a", "b"], {})

    found = plan_store.find_incomplete()

    assert found is not None
    assert found["id"] == pid


def test_find_incomplete_returns_none_when_no_plans():
    assert plan_store.find_incomplete() is None


def test_update_progress_persists_context_and_index():
    pid = plan_store.new_id()
    plan_store.save(pid, "tarefa", ["a", "b", "c"], {"tarefa_original": "tarefa"})

    plan_store.update_progress(pid, 1, {"tarefa_original": "tarefa", "passo_1": "resultado do passo 1"})

    found = plan_store.find_incomplete()
    assert found["current_index"] == 1
    assert found["context"]["passo_1"] == "resultado do passo 1"


def test_finish_removes_plan_so_it_stops_being_incomplete():
    pid = plan_store.new_id()
    plan_store.save(pid, "tarefa", ["a"], {})

    plan_store.finish(pid)

    assert plan_store.find_incomplete() is None
    assert not os.path.exists(plan_store._path(pid))


def test_finish_on_missing_plan_does_not_raise():
    plan_store.finish("nao-existe")  # não deve levantar exceção


def test_find_incomplete_ignores_finished_or_cancelled_status():
    pid = plan_store.new_id()
    plan_store.save(pid, "tarefa", ["a"], {})
    with open(plan_store._path(pid), "r", encoding="utf-8") as f:
        data = json.load(f)
    data["status"] = "done"
    with open(plan_store._path(pid), "w", encoding="utf-8") as f:
        json.dump(data, f)

    assert plan_store.find_incomplete() is None


def test_find_incomplete_returns_most_recently_updated():
    pid1 = plan_store.new_id()
    plan_store.save(pid1, "tarefa antiga", ["a"], {})
    time.sleep(0.02)
    pid2 = plan_store.new_id()
    plan_store.save(pid2, "tarefa nova", ["a"], {})
    plan_store.update_progress(pid2, 0, {})  # bump updated timestamp explicitamente

    found = plan_store.find_incomplete()

    assert found["id"] == pid2
