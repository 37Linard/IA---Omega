import threading
import time

import agent as agent_mod
from agent import ReActAgent


class _FakeTool:
    def __init__(self, name):
        self.name = name

    def run(self, input_data):
        return f"ran {self.name}"


def _bare_agent(tools):
    """ReActAgent sem passar por __init__ — evita Memory()/UserProfile() reais
    (LanceDB, Redis, arquivos em workspace/) que __init__ inicializa."""
    a = ReActAgent.__new__(ReActAgent)
    a.tools       = {t.name: t for t in tools}
    a._tool_calls = 0
    a._cancel     = threading.Event()
    a._emit       = None
    return a


def test_tool_risk_uses_configured_tiers_and_default():
    a = ReActAgent.__new__(ReActAgent)
    assert a._tool_risk("terminal") == "destructive"
    assert a._tool_risk("read_file") == "read"
    assert a._tool_risk("write_file") == "write"
    assert a._tool_risk("plugin_tool_desconhecido") == "write"  # DEFAULT_TOOL_RISK


def test_execute_tool_runs_directly_when_hitl_disabled(monkeypatch):
    monkeypatch.setattr(agent_mod, "HITL_ENABLED", False)
    monkeypatch.setattr(agent_mod.audit, "log_action", lambda *a, **k: None)
    a = _bare_agent([_FakeTool("terminal")])

    result = a._execute_tool("terminal", {"command": "ls"})

    assert result == "ran terminal"


def test_execute_tool_gates_destructive_tool_and_runs_when_approved(monkeypatch):
    monkeypatch.setattr(agent_mod, "HITL_ENABLED", True)
    monkeypatch.setattr(agent_mod, "HITL_GATE_TIERS", ["destructive"])
    monkeypatch.setattr(agent_mod.audit, "log_action", lambda *a, **k: None)
    a = _bare_agent([_FakeTool("terminal")])
    a._hitl_gate = lambda action, action_input: True

    result = a._execute_tool("terminal", {"command": "ls"})

    assert result == "ran terminal"


def test_execute_tool_blocks_destructive_tool_when_rejected(monkeypatch):
    monkeypatch.setattr(agent_mod, "HITL_ENABLED", True)
    monkeypatch.setattr(agent_mod, "HITL_GATE_TIERS", ["destructive"])
    a = _bare_agent([_FakeTool("terminal")])
    a._hitl_gate = lambda action, action_input: False

    result = a._execute_tool("terminal", {"command": "ls"})

    assert "cancelada" in result.lower()


def test_execute_tool_skips_gate_for_tiers_not_configured(monkeypatch):
    monkeypatch.setattr(agent_mod, "HITL_ENABLED", True)
    monkeypatch.setattr(agent_mod, "HITL_GATE_TIERS", ["destructive"])
    monkeypatch.setattr(agent_mod.audit, "log_action", lambda *a, **k: None)
    a = _bare_agent([_FakeTool("read_file")])

    def boom(*args, **kwargs):
        raise AssertionError("hitl gate nao deveria ser chamado pra tool de tier 'read'")
    a._hitl_gate = boom

    result = a._execute_tool("read_file", {"path": "workspace/nota.txt"})

    assert result == "ran read_file"


def test_hitl_gate_emits_risk_tier_and_respects_approval():
    registry = agent_mod._HITL_REGISTRY
    a = ReActAgent.__new__(ReActAgent)
    a._cancel = threading.Event()
    emitted = []
    a._emit = emitted.append

    result_box = {}

    def call_gate():
        result_box["approved"] = a._hitl_gate("terminal", {"cmd": "ls"})

    t = threading.Thread(target=call_gate)
    t.start()
    try:
        # espera o hitl_gate publicar o pedido no registry global antes de aprovar
        for _ in range(50):
            if registry:
                break
            time.sleep(0.02)
        hitl_id = next(iter(registry))
        registry[hitl_id]["approved"] = True
        registry[hitl_id]["event"].set()
        t.join(timeout=5)
    finally:
        registry.clear()

    assert emitted[0]["type"] == "hitl_request"
    assert emitted[0]["action"] == "terminal"
    assert emitted[0]["risk"] == "destructive"
    assert result_box["approved"] is True
