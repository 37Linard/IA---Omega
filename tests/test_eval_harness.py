import time

from eval_harness import _run_task, _ACTION_RE


def test_action_regex_extracts_tool_name():
    assert _ACTION_RE.match("run_python({'code': 'print(1)'})").group(1) == "run_python"
    assert _ACTION_RE.match("get_crypto({\"symbol\": \"bitcoin\"})").group(1) == "get_crypto"
    assert _ACTION_RE.match("not a tool call") is None


class _FakeOrchestrator:
    def __init__(self, answer, events=(), delay=0):
        self.answer   = answer
        self.events   = events
        self.delay    = delay
        self.cancelled = False

    def run(self, task, max_steps=0, step_callback=None):
        for ev in self.events:
            step_callback(ev)
        if self.delay:
            time.sleep(self.delay)
        return self.answer

    def cancel(self, reason=""):
        self.cancelled = True


def _action_event(call: str) -> dict:
    return {"type": "action", "content": call}


def test_run_task_passes_when_all_criteria_met():
    orch = _FakeOrchestrator(
        answer="o resultado é 391",
        events=[_action_event("run_python({'code': 'print(391)'})")],
    )
    task_def = {
        "id": "t1", "task": "calcule", "must_contain": ["391"],
        "must_not_contain": ["erro"], "expected_tools": ["run_python"],
        "forbidden_tools": ["terminal"], "max_seconds": 5,
    }

    result = _run_task(orch, task_def)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["tools_called"] == ["run_python"]


def test_run_task_fails_when_must_contain_missing():
    orch = _FakeOrchestrator(answer="não sei calcular isso")
    task_def = {"id": "t1", "task": "x", "must_contain": ["391"], "max_seconds": 5}

    result = _run_task(orch, task_def)

    assert result["passed"] is False
    assert any("391" in f for f in result["failures"])


def test_run_task_fails_when_must_not_contain_present():
    orch = _FakeOrchestrator(answer="Erro: algo deu errado")
    task_def = {"id": "t1", "task": "x", "must_not_contain": ["erro:"], "max_seconds": 5}

    result = _run_task(orch, task_def)

    assert result["passed"] is False
    assert any("erro:" in f for f in result["failures"])


def test_run_task_fails_when_expected_tool_not_called():
    orch = _FakeOrchestrator(answer="ok", events=[_action_event("web_search({'query': 'bitcoin'})")])
    task_def = {"id": "t1", "task": "x", "expected_tools": ["get_crypto"], "max_seconds": 5}

    result = _run_task(orch, task_def)

    assert result["passed"] is False
    assert result["tools_called"] == ["web_search"]
    assert any("get_crypto" in f for f in result["failures"])


def test_run_task_fails_when_forbidden_tool_called():
    orch = _FakeOrchestrator(answer="ok", events=[_action_event("terminal({'cmd': 'ls'})")])
    task_def = {"id": "t1", "task": "x", "forbidden_tools": ["terminal"], "max_seconds": 5}

    result = _run_task(orch, task_def)

    assert result["passed"] is False
    assert any("terminal" in f for f in result["failures"])


def test_run_task_times_out_and_cancels_orchestrator():
    orch = _FakeOrchestrator(answer="tarde demais", delay=0.3)
    task_def = {"id": "t1", "task": "x", "max_seconds": 0.05}

    result = _run_task(orch, task_def)

    assert result["passed"] is False
    assert any("timeout" in f for f in result["failures"])
    assert orch.cancelled is True
