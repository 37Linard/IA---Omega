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


class _CancelAfterN:
    """Fake threading.Event: is_set() fica False pelas primeiras `n` chamadas,
    True dai em diante. Simula um cancelamento/timeout que chega bem no meio
    de um retry do self-consistency (2º step do loop), sem precisar de thread
    real nem sleep."""

    def __init__(self, n):
        self._calls = 0
        self._n = n

    def is_set(self):
        self._calls += 1
        return self._calls > self._n


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
        # Só 1 entrada: a 2ª avaliação de reflection (depois da troca de modelo)
        # roda no alt_llm, não no primary_llm — ver _ScriptedLLM.generate, que
        # distingue a chamada pelo self.llm ATUAL, não por qual LLM criou o
        # candidato. Uma 2ª entrada aqui nunca seria consumida (dado morto).
        reflect_jsons=['{"score": 2, "issues": [], "hint": ""}'],
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


def test_llm_restored_to_primary_when_cancelled_mid_retry(monkeypatch):
    """Code-review finding (pos-Task 2): self.llm só era restaurado pro
    _primary_llm no caminho normal Final Answer -> voto. Mas run() tem outros
    caminhos de retorno (cancelamento/timeout no topo do loop, curto-circuito
    de generate_image/generate_chart, limite de steps) que podem disparar
    DEPOIS que um retry já trocou self.llm pro modelo alternativo. Se
    qualquer um desses vier antes de outro Final Answer, self.llm ficava
    vazando o modelo alternativo pro resto da sessão -- e ReActAgent é
    reusado entre run() (api.py e main.py chamam agent.run() em loop na
    mesma instância), entao o PRÓXIMO run() prometeria o modelo alternativo a
    _primary_llm silenciosamente. Este teste força esse cenário: 1ª tentativa
    (primary) sai fraca -> retry troca pra alt-model -> antes do 2º step
    conseguir gerar qualquer coisa, um cancelamento chega no topo do loop."""
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)
    monkeypatch.setattr(agent_mod, "SELF_CONSISTENCY_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(agent_mod, "ENSEMBLE_MODELS", ["primary-model", "alt-model"])

    primary_llm = _ScriptedLLM(
        model="primary-model",
        react_responses=["Thought: 1.\nFinal Answer: tentativa 1 (principal)"],
        reflect_jsons=['{"score": 2, "issues": [], "hint": ""}'],
    )
    # alt_llm nunca deveria ser chamado -- o cancelamento bate antes de
    # qualquer generate() nele. Sem react_responses/reflect_jsons de propósito:
    # se o código chamasse alt_llm.generate por engano, o teste quebraria com
    # IndexError em vez de passar silenciosamente.
    alt_llm = _ScriptedLLM(model="alt-model")

    monkeypatch.setattr(agent_mod, "OllamaLLM", lambda model: alt_llm)

    a = _bare_agent(primary_llm)
    # False no check do step 0 (deixa rodar Final Answer + reflection + retry);
    # True no check do step 1 (cancela antes do 2º generate) -- ver Step 897-901
    # do agent.py, checado no topo de cada iteração do loop ReAct.
    a._cancel = _CancelAfterN(1)

    result = a.run(TASK, step_callback=None)

    assert result == "Cancelado."
    assert a.llm is primary_llm
    assert a.llm.model == "primary-model"
    assert a.llm is a._primary_llm


def test_reflect_always_uses_primary_llm_not_current_attempt_model(monkeypatch):
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)
    monkeypatch.setattr(agent_mod, "SELF_CONSISTENCY_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(agent_mod, "ENSEMBLE_MODELS", ["primary-model", "alt-model"])

    primary_llm = _ScriptedLLM(
        model="primary-model",
        react_responses=["Thought: 1.\nFinal Answer: tentativa 1 (principal)"],
        # As DUAS avaliações de reflection devem vir do primary -- mesmo a que
        # avalia a resposta gerada pelo modelo alternativo.
        reflect_jsons=[
            '{"score": 2, "issues": [], "hint": ""}',
            '{"score": 5, "issues": [], "hint": ""}',
        ],
        vote_responses=["1"],
    )
    alt_llm = _ScriptedLLM(
        model="alt-model",
        react_responses=["Thought: 2.\nFinal Answer: tentativa 2 (alternativo)"],
        reflect_jsons=[],  # vazio de propósito: se _reflect chamar isto, IndexError (pop de lista vazia)
    )

    monkeypatch.setattr(agent_mod, "OllamaLLM", lambda model: alt_llm)

    a = _bare_agent(primary_llm)
    result = a.run(TASK, step_callback=None)

    assert result == "tentativa 2 (alternativo)"
    assert alt_llm.reflect_jsons == []  # nunca foi tocado -- prova que _reflect nunca usou o alt_llm
    assert primary_llm.reflect_jsons == []  # as 2 avaliações vieram todas do primary
