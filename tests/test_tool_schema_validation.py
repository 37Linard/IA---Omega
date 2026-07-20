import threading

import agent as agent_mod
from agent import ReActAgent
from tools._schema import validate


def test_validate_passes_unknown_tool():
    assert validate("tool_sem_schema", {}) == ""


def test_validate_passes_non_dict_input():
    # já validado em outro lugar (agent._parse_response) — não é responsabilidade daqui
    assert validate("run_python", "codigo solto") == ""


def test_validate_catches_missing_required_field():
    err = validate("run_python", {})
    assert "code" in err
    assert "obrigatório" in err


def test_validate_passes_when_required_field_present():
    assert validate("run_python", {"code": "print(1)"}) == ""


def test_validate_required_any_accepts_either_alternative():
    assert validate("generate_image", {"prompt": "um gato"}) == ""
    assert validate("generate_image", {"description": "um gato"}) == ""
    err = validate("generate_image", {})
    assert "prompt" in err and "description" in err


def test_validate_catches_invalid_enum_value():
    err = validate("browser", {"action": "voar"})
    assert "voar" in err
    assert "invalido" in err.lower() or "inválido" in err.lower()


def test_validate_catches_missing_field_for_specific_action_branch():
    err = validate("browser", {"action": "goto"})  # falta 'url'
    assert "url" in err


def test_validate_passes_when_action_branch_satisfied():
    assert validate("browser", {"action": "goto", "url": "https://example.com"}) == ""
    assert validate("browser", {"action": "screenshot"}) == ""  # sem required_by_action pra essa branch


def test_validate_required_by_action_only_triggers_for_matching_action():
    # clipboard 'write' exige 'text', mas 'read' (default) nao passa por essa checagem aqui
    assert validate("clipboard", {"action": "read"}) == ""
    err = validate("clipboard", {"action": "write"})
    assert "text" in err


class _FakeTool:
    def __init__(self, name):
        self.name = name
        self.called = False

    def run(self, input_data):
        self.called = True
        return "ok"


def _bare_agent(tools):
    a = ReActAgent.__new__(ReActAgent)
    a.tools       = {t.name: t for t in tools}
    a._tool_calls = 0
    a._cancel     = threading.Event()
    a._emit       = None
    return a


def test_execute_tool_rejects_malformed_input_without_running_tool(monkeypatch):
    monkeypatch.setattr(agent_mod, "HITL_ENABLED", False)
    fake = _FakeTool("run_python")
    a = _bare_agent([fake])

    result = a._execute_tool("run_python", {})  # falta 'code'

    assert "code" in result
    assert fake.called is False


def test_execute_tool_skips_hitl_for_malformed_destructive_call(monkeypatch):
    # input malformado numa tool destrutiva nao deveria nem chegar a pedir aprovacao humana
    monkeypatch.setattr(agent_mod, "HITL_ENABLED", True)
    monkeypatch.setattr(agent_mod, "HITL_GATE_TIERS", ["destructive"])
    fake = _FakeTool("terminal")
    a = _bare_agent([fake])

    def boom(*args, **kwargs):
        raise AssertionError("nao deveria pedir aprovacao humana pra input ja invalido")
    a._hitl_gate = boom

    result = a._execute_tool("terminal", {})  # falta 'command'

    assert "command" in result
    assert fake.called is False


def test_execute_tool_runs_normally_when_input_valid(monkeypatch):
    monkeypatch.setattr(agent_mod, "HITL_ENABLED", False)
    monkeypatch.setattr(agent_mod.audit, "log_action", lambda *a, **k: None)
    fake = _FakeTool("run_python")
    a = _bare_agent([fake])

    result = a._execute_tool("run_python", {"code": "print(1)"})

    assert result == "ok"
    assert fake.called is True
