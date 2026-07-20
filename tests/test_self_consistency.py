import threading

import agent as agent_mod
from agent import ReActAgent


class _StubMemory:
    def get_context(self, task="", session_id=""):
        return ""

    def save_session_with_llm(self, *a, **k):
        pass


class _StubProfile:
    def observe_message(self, text):
        pass

    def increment_interactions(self):
        pass

    def get_system_context(self):
        return ""


class _ScriptedLLM:
    """LLM falso: distingue a chamada de raciocínio ReAct da chamada de reflection
    pelo conteúdo do prompt (a de reflection sempre pede o JSON de score)."""

    def __init__(self, react_responses, reflect_jsons):
        self.model = "test-model"
        self.react_responses = list(react_responses)
        self.reflect_jsons = list(reflect_jsons)

    def generate(self, prompt, on_token=None):
        if "Avalie se a resposta" in prompt:
            return self.reflect_jsons.pop(0)
        resp = self.react_responses.pop(0)
        if on_token:
            for ch in resp:
                on_token(ch)
        return resp


def _bare_agent(llm):
    a = ReActAgent.__new__(ReActAgent)
    a.llm                = llm
    a.tools               = {}
    a.memory              = _StubMemory()
    a.profile             = _StubProfile()
    a._cancel             = threading.Event()
    a._cancel_reason      = "usuário"
    a.conversation        = []
    a.specialist_context  = ""
    a.session_id          = ""
    a._emit               = None
    return a


TASK = "escreva um resumo curto"  # curto, sem sequence word -> nunca cai em compound/conversational


def test_self_consistency_keeps_first_answer_when_it_scored_higher(monkeypatch):
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)  # 3 dispara retry
    llm = _ScriptedLLM(
        react_responses=[
            "Thought: pronto.\nFinal Answer: resposta A",
            "Thought: reescrevendo.\nFinal Answer: resposta B (reescrita, mas pior)",
        ],
        reflect_jsons=[
            '{"score": 3, "issues": ["faltou contexto"], "hint": "adicione contexto"}',
            '{"score": 2, "issues": [], "hint": ""}',
        ],
    )
    a = _bare_agent(llm)

    result = a.run(TASK, step_callback=None)

    assert result == "resposta A"  # 1a (score 3) bateu a 2a (score 2) — self-consistency


def test_self_consistency_keeps_second_answer_when_rewrite_actually_improved(monkeypatch):
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)
    llm = _ScriptedLLM(
        react_responses=[
            "Thought: pronto.\nFinal Answer: resposta A fraca",
            "Thought: reescrevendo.\nFinal Answer: resposta B, bem melhor",
        ],
        reflect_jsons=[
            '{"score": 2, "issues": ["ruim"], "hint": "melhore"}',
            '{"score": 5, "issues": [], "hint": ""}',
        ],
    )
    a = _bare_agent(llm)

    result = a.run(TASK, step_callback=None)

    assert result == "resposta B, bem melhor"  # 2a (score 5) bateu a 1a (score 2) — comportamento normal


def test_no_retry_when_first_score_already_passes_threshold(monkeypatch):
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 3)
    llm = _ScriptedLLM(
        react_responses=["Thought: pronto.\nFinal Answer: resposta boa de primeira"],
        reflect_jsons=['{"score": 4, "issues": [], "hint": ""}'],
    )
    a = _bare_agent(llm)

    result = a.run(TASK, step_callback=None)

    assert result == "resposta boa de primeira"
    assert llm.react_responses == []  # só uma chamada de raciocínio — nunca tentou reescrever
