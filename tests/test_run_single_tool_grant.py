"""Regressão: 'Agende: todo dia às 9h me avise o preço do bitcoin' classificava
como especialista Pesquisador (por causa de 'bitcoin') mas sem schedule_task
disponível (só em 'comunicacao') e sem palavra de sequência ('e'/'depois') pra
disparar o toolset ampliado de is_multi_domain — o modelo inventava uma tool
que não existe. _run_single agora usa domain_hits() puro (>=2 domínios) em vez
de is_multi_domain pra decidir SÓ a ampliação de toolset de um especialista já
escolhido (não decide reestruturar em Plan-then-Execute, então não precisa da
mesma cautela de is_multi_domain)."""
import threading

import orchestrator
from orchestrator import OrchestratorAgent, SPECIALISTS


class _DummyTool:
    def __init__(self, name):
        self.name = name


class _FakeReActAgent:
    last_kwargs = None

    def __init__(self, **kwargs):
        type(self).last_kwargs = kwargs
        self.tools = {t.name: t for t in kwargs.get("tools", [])}

    def cancel(self, reason="usuário"):
        pass

    def run(self, task, step_callback=None):
        return "ok"


def _bare_orchestrator(monkeypatch, classify_as: str):
    monkeypatch.setattr(orchestrator.OrchestratorAgent, "_llm_cache", {})
    monkeypatch.setattr(orchestrator, "ReActAgent", _FakeReActAgent, raising=False)
    import agent as agent_mod
    monkeypatch.setattr(agent_mod, "ReActAgent", _FakeReActAgent)

    o = OrchestratorAgent.__new__(OrchestratorAgent)
    o.all_tools  = {name: _DummyTool(name) for spec in SPECIALISTS.values() for name in spec["tools"]}
    o.memory     = None
    o.session_id = ""
    o._cancel    = threading.Event()
    o._lock      = threading.Lock()
    o._active    = []
    o._classify  = lambda task: classify_as
    return o


TASK = "Agende: todo dia às 9h me avise o preço do bitcoin"


def test_single_task_without_sequence_word_still_grants_cross_domain_tool(monkeypatch):
    o = _bare_orchestrator(monkeypatch, classify_as="pesquisador")

    o._run_single(TASK, step_callback=None)

    got = {t.name for t in _FakeReActAgent.last_kwargs["tools"]}
    assert "schedule_task" in got  # veio do domínio "comunicacao" mesmo sem "e"/"depois"
    assert "get_crypto" in got     # domínio classificado (pesquisador) continua disponível


def test_single_domain_task_stays_scoped_to_its_own_specialist(monkeypatch):
    o = _bare_orchestrator(monkeypatch, classify_as="pesquisador")

    o._run_single("qual o preço do bitcoin agora?", step_callback=None)

    got = {t.name for t in _FakeReActAgent.last_kwargs["tools"]}
    assert got == set(SPECIALISTS["pesquisador"]["tools"])  # só 1 domínio detectado -> sem ampliação
    assert "schedule_task" not in got
