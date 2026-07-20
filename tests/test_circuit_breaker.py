import threading

import pytest

import agent as agent_mod
import circuit_breaker as cb
from agent import ReActAgent


@pytest.fixture(autouse=True)
def _reset_breaker():
    cb.reset()
    yield
    cb.reset()


def test_closed_by_default():
    open_, remaining = cb.is_open("qualquer_tool")
    assert open_ is False
    assert remaining == 0.0


def test_stays_closed_below_threshold():
    cb.record_result("t1", success=False)
    cb.record_result("t1", success=False)  # 2 falhas — threshold é 3
    open_, _ = cb.is_open("t1")
    assert open_ is False


def test_opens_after_threshold_consecutive_failures():
    for _ in range(3):
        cb.record_result("t1", success=False)
    open_, remaining = cb.is_open("t1")
    assert open_ is True
    assert remaining > 0


def test_success_resets_failure_streak():
    cb.record_result("t1", success=False)
    cb.record_result("t1", success=False)
    cb.record_result("t1", success=True)  # reseta
    cb.record_result("t1", success=False)
    cb.record_result("t1", success=False)
    open_, _ = cb.is_open("t1")
    assert open_ is False  # só 2 falhas desde o reset, não abriu


def test_half_open_after_cooldown(monkeypatch):
    for _ in range(3):
        cb.record_result("t1", success=False)
    assert cb.is_open("t1")[0] is True

    # simula cooldown expirado voltando o relogio pro passado
    cb._state["t1"]["opened_at"] -= (cb.COOLDOWN_SECONDS + 1)

    open_, remaining = cb.is_open("t1")
    assert open_ is False
    assert remaining == 0.0


def test_status_reports_open_tools():
    for _ in range(3):
        cb.record_result("quebrada", success=False)
    cb.record_result("saudavel", success=True)

    rows = {r["tool"]: r for r in cb.status()}

    assert rows["quebrada"]["open"] is True
    assert rows["quebrada"]["failures"] == 3
    assert rows["saudavel"]["open"] is False
    assert rows["saudavel"]["failures"] == 0


def test_reset_specific_tool_only():
    for _ in range(3):
        cb.record_result("a", success=False)
        cb.record_result("b", success=False)

    cb.reset("a")

    assert cb.is_open("a")[0] is False
    assert cb.is_open("b")[0] is True


# ── Integração com agent.py:_execute_tool ───────────────────────────────────

class _FakeTool:
    def __init__(self, name, results):
        self.name = name
        self.results = list(results)
        self.calls = 0

    def run(self, input_data):
        self.calls += 1
        return self.results.pop(0)


def _bare_agent(tools):
    a = ReActAgent.__new__(ReActAgent)
    a.tools       = {t.name: t for t in tools}
    a._tool_calls = 0
    a._cancel     = threading.Event()
    a._emit       = None
    return a


def test_execute_tool_opens_circuit_after_repeated_failures(monkeypatch):
    monkeypatch.setattr(agent_mod, "HITL_ENABLED", False)
    monkeypatch.setattr(agent_mod.audit, "log_action", lambda *a, **k: None)
    fake = _FakeTool("run_python", ["Erro: falhou 1", "Erro: falhou 2", "Erro: falhou 3", "Erro: falhou 4"])
    a = _bare_agent([fake])

    for _ in range(3):
        a._execute_tool("run_python", {"code": f"x = {_}"})

    result = a._execute_tool("run_python", {"code": "outra tentativa"})

    assert "circuito aberto" in result.lower()
    assert fake.calls == 3  # a 4a chamada foi bloqueada antes de rodar a tool


def test_execute_tool_success_keeps_circuit_closed(monkeypatch):
    monkeypatch.setattr(agent_mod, "HITL_ENABLED", False)
    monkeypatch.setattr(agent_mod.audit, "log_action", lambda *a, **k: None)
    fake = _FakeTool("run_python", ["ok"] * 5)
    a = _bare_agent([fake])

    for i in range(5):
        result = a._execute_tool("run_python", {"code": f"x = {i}"})
        assert result == "ok"

    assert fake.calls == 5
