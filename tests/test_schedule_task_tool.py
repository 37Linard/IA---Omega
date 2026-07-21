import tools.schedule_task_tool as st
from tools._schema import validate
from tools.schedule_task_tool import ScheduleTaskTool


def test_create_persists_task_and_returns_id(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "TASKS_FILE", str(tmp_path / "scheduled_tasks.json"))
    tool = ScheduleTaskTool()

    result = tool.run({"action": "create", "task": "resuma as notícias", "hour": 9, "minute": 0})

    assert "agendada com sucesso" in result
    tasks = st.load_scheduled_tasks()
    assert len(tasks) == 1
    assert tasks[0]["task"] == "resuma as notícias"
    assert tasks[0]["hour"] == 9
    assert tasks[0]["minute"] == 0
    assert tasks[0]["id"] in result


def test_create_rejects_missing_task():
    tool = ScheduleTaskTool()
    result = tool.run({"action": "create", "hour": 9})
    assert "task" in result.lower() and "obrigatório" in result.lower()


def test_create_rejects_invalid_hour():
    tool = ScheduleTaskTool()
    result = tool.run({"action": "create", "task": "algo", "hour": 25})
    assert "hour" in result


def test_list_shows_created_tasks(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "TASKS_FILE", str(tmp_path / "scheduled_tasks.json"))
    tool = ScheduleTaskTool()
    tool.run({"action": "create", "task": "resuma as notícias", "hour": 9, "minute": 0, "label": "Resumo diário"})

    result = tool.run({"action": "list"})

    assert "Resumo diário" in result
    assert "09:00" in result


def test_list_empty_when_no_tasks(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "TASKS_FILE", str(tmp_path / "scheduled_tasks.json"))
    tool = ScheduleTaskTool()

    assert tool.run({"action": "list"}) == "Nenhuma tarefa agendada."


def test_remove_deletes_task_by_id(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "TASKS_FILE", str(tmp_path / "scheduled_tasks.json"))
    tool = ScheduleTaskTool()
    create_result = tool.run({"action": "create", "task": "algo", "hour": 9})
    tid = st.load_scheduled_tasks()[0]["id"]

    result = tool.run({"action": "remove", "id": tid})

    assert "removida" in result
    assert st.load_scheduled_tasks() == []


def test_remove_unknown_id_reports_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "TASKS_FILE", str(tmp_path / "scheduled_tasks.json"))
    tool = ScheduleTaskTool()

    result = tool.run({"action": "remove", "id": "nao-existe"})

    assert result.startswith("Erro:")
    assert "nenhuma tarefa agendada com id" in result.lower()


def test_defaults_to_create_when_action_omitted(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "TASKS_FILE", str(tmp_path / "scheduled_tasks.json"))
    tool = ScheduleTaskTool()

    result = tool.run({"task": "algo", "hour": 10})

    assert "agendada com sucesso" in result


def test_schema_requires_action():
    err = validate("schedule_task", {})
    assert "action" in err


def test_schema_requires_task_and_hour_for_create():
    err = validate("schedule_task", {"action": "create"})
    assert "task" in err or "hour" in err
    assert validate("schedule_task", {"action": "create", "task": "x", "hour": 9}) == ""


def test_schema_requires_id_for_remove():
    err = validate("schedule_task", {"action": "remove"})
    assert "id" in err
    assert validate("schedule_task", {"action": "remove", "id": "abc"}) == ""


def test_schema_rejects_invalid_action():
    err = validate("schedule_task", {"action": "voar"})
    assert "voar" in err
