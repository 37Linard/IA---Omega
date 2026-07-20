import threading

import agent as agent_mod
import orchestrator
from orchestrator import OrchestratorAgent, SPECIALISTS, tools_for_domains


def test_tools_for_domains_unions_only_requested_domains():
    result = tools_for_domains({"pesquisador", "arquivos"})
    expected = sorted(set(SPECIALISTS["pesquisador"]["tools"]) | set(SPECIALISTS["arquivos"]["tools"]))
    assert result == expected
    # não vaza tools de domínios não pedidos (terminal/git são de "codigo")
    assert "terminal" not in result
    assert "git" not in result


def test_tools_for_domains_ignores_unknown_domain():
    assert tools_for_domains({"nao_existe"}) == []


class _DummyTool:
    """Objeto mínimo com .name e capaz de receber atributo — mimetiza tool real
    o suficiente pra orchestrator._create_specialist rodar sem heavy init."""
    def __init__(self, name):
        self.name = name


class _FakeReActAgent:
    last_kwargs = None

    def __init__(self, **kwargs):
        type(self).last_kwargs = kwargs
        self.tools = {t.name: t for t in kwargs.get("tools", [])}

    def cancel(self, reason="usuário"):
        pass


def _bare_orchestrator(monkeypatch):
    monkeypatch.setattr(orchestrator.OrchestratorAgent, "_llm_cache", {})
    monkeypatch.setattr(agent_mod, "ReActAgent", _FakeReActAgent)
    o = OrchestratorAgent.__new__(OrchestratorAgent)
    o.all_tools = {name: _DummyTool(name) for spec in SPECIALISTS.values() for name in spec["tools"]}
    o.memory      = None
    o.session_id  = ""
    o._cancel     = threading.Event()
    o._lock       = threading.Lock()
    o._active     = []
    return o


def _tool_names(kwargs):
    return {t.name for t in kwargs["tools"]}


def test_create_specialist_default_scopes_to_its_own_tools(monkeypatch):
    o = _bare_orchestrator(monkeypatch)

    o._create_specialist("pesquisador")

    assert _tool_names(_FakeReActAgent.last_kwargs) == set(SPECIALISTS["pesquisador"]["tools"])


def test_create_specialist_explicit_tool_names_restricts_to_union(monkeypatch):
    o = _bare_orchestrator(monkeypatch)

    union = tools_for_domains({"pesquisador", "arquivos"})
    o._create_specialist("pesquisador", tool_names=union)

    got = _tool_names(_FakeReActAgent.last_kwargs)
    assert got == set(union)
    assert "terminal" not in got  # dominio "codigo" nao foi pedido


def test_create_specialist_geral_gets_everything(monkeypatch):
    o = _bare_orchestrator(monkeypatch)

    o._create_specialist("geral")

    assert _tool_names(_FakeReActAgent.last_kwargs) == set(o.all_tools.keys())
