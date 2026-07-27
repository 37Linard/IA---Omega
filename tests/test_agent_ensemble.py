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
    """Mesmo estilo de tests/test_self_consistency.py — distingue a chamada
    pelo conteúdo do prompt (ReAct/reflection/voto)."""

    def __init__(self, model, react_responses=None, reflect_jsons=None, vote_responses=None):
        self.model = model
        self.react_responses = list(react_responses or [])
        self.reflect_jsons = list(reflect_jsons or [])
        self.vote_responses = list(vote_responses or [])

    def generate(self, prompt, on_token=None):
        if "Avalie se a resposta" in prompt:
            return self.reflect_jsons.pop(0)
        if "Candidatos de resposta" in prompt:
            return self.vote_responses.pop(0)
        resp = self.react_responses.pop(0)
        if on_token:
            for ch in resp:
                on_token(ch)
        return resp


def _bare_agent(llm):
    a = ReActAgent.__new__(ReActAgent)
    a.llm                = llm
    a.tools              = {}
    a.memory             = _StubMemory()
    a.profile            = _StubProfile()
    a._cancel            = threading.Event()
    a._cancel_reason     = "usuário"
    a.conversation       = []
    a.specialist_context = ""
    a.session_id         = ""
    a._emit              = None
    return a


TASK = "escreva um resumo curto"  # mesmo task-sentinel de test_self_consistency.py


def test_second_attempt_uses_ensemble_alternate_model(monkeypatch):
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)
    monkeypatch.setattr(agent_mod, "SELF_CONSISTENCY_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(agent_mod, "ENSEMBLE_MODELS", ["primary-model", "alt-model"])

    primary_llm = _ScriptedLLM(
        model="primary-model",
        react_responses=["Thought: 1.\nFinal Answer: tentativa 1 (principal)"],
        reflect_jsons=[
            '{"score": 2, "issues": [], "hint": ""}',
            '{"score": 5, "issues": [], "hint": ""}',
        ],
        vote_responses=["1"],
    )
    alt_llm = _ScriptedLLM(
        model="alt-model",
        react_responses=["Thought: 2.\nFinal Answer: tentativa 2 (alternativo)"],
    )

    constructed_models = []

    def fake_ollama_llm(model):
        constructed_models.append(model)
        assert model == "alt-model"  # só o alternativo deveria ser construído
        return alt_llm

    monkeypatch.setattr(agent_mod, "OllamaLLM", fake_ollama_llm)

    a = _bare_agent(primary_llm)
    result = a.run(TASK, step_callback=None)

    assert constructed_models == ["alt-model"]
    assert result == "tentativa 2 (alternativo)"
