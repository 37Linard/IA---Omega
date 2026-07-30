import threading

import agent as agent_mod
from agent import ReActAgent


class _FakeRagTool:
    name = "rag_search"

    def __init__(self, last_sources):
        self._last_sources = last_sources
        self.last_sources = []

    def run(self, input_data):
        self.last_sources = self._last_sources
        return "Trechos mais relevantes para: 'x'"


def _bare_agent(tools, emit=None):
    a = ReActAgent.__new__(ReActAgent)
    a.tools       = {t.name: t for t in tools}
    a._tool_calls = 0
    a._cancel     = threading.Event()
    a._emit       = emit
    return a


def test_execute_tool_emits_rag_sources_event(monkeypatch):
    monkeypatch.setattr(agent_mod, "HITL_ENABLED", False)
    monkeypatch.setattr(agent_mod.audit, "log_action", lambda *a, **k: None)

    sources = [{"file": "contrato.pdf", "page": 2, "score": 0.9, "excerpt": "cláusula de rescisão"}]
    emitted = []
    a = _bare_agent([_FakeRagTool(sources)], emit=lambda data: emitted.append(data))

    a._execute_tool("rag_search", {"query": "rescisão"})

    rag_events = [e for e in emitted if e["type"] == "rag_sources"]
    assert len(rag_events) == 1
    assert rag_events[0]["sources"] == sources


def test_execute_tool_skips_event_when_no_sources_found(monkeypatch):
    monkeypatch.setattr(agent_mod, "HITL_ENABLED", False)
    monkeypatch.setattr(agent_mod.audit, "log_action", lambda *a, **k: None)

    emitted = []
    a = _bare_agent([_FakeRagTool([])], emit=lambda data: emitted.append(data))

    a._execute_tool("rag_search", {"query": "nada"})

    assert not any(e["type"] == "rag_sources" for e in emitted)


def test_other_tools_never_emit_rag_sources(monkeypatch):
    class _FakeOtherTool:
        name = "terminal"

        def run(self, input_data):
            return "ran terminal"

    monkeypatch.setattr(agent_mod, "HITL_ENABLED", False)
    monkeypatch.setattr(agent_mod.audit, "log_action", lambda *a, **k: None)

    emitted = []
    a = _bare_agent([_FakeOtherTool()], emit=lambda data: emitted.append(data))

    a._execute_tool("terminal", {"command": "ls"})

    assert not any(e["type"] == "rag_sources" for e in emitted)
