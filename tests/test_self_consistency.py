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
    """LLM falso: distingue a chamada de raciocínio ReAct, a de reflection (pede
    JSON de score) e a de voto do self-consistency (lista "Candidatos de
    resposta") pelo conteúdo do prompt."""

    def __init__(self, react_responses, reflect_jsons, vote_responses=None):
        self.model = "test-model"
        self.react_responses = list(react_responses)
        self.reflect_jsons = list(reflect_jsons)
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


def test_self_consistency_keeps_first_answer_when_vote_picks_it(monkeypatch):
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)  # 3 dispara retry
    monkeypatch.setattr(agent_mod, "SELF_CONSISTENCY_MAX_ATTEMPTS", 2)  # trava no boundary de 2 tentativas
    llm = _ScriptedLLM(
        react_responses=[
            "Thought: pronto.\nFinal Answer: resposta A",
            "Thought: reescrevendo.\nFinal Answer: resposta B (reescrita, mas pior)",
        ],
        reflect_jsons=[
            '{"score": 3, "issues": ["faltou contexto"], "hint": "adicione contexto"}',
            '{"score": 2, "issues": [], "hint": ""}',
        ],
        vote_responses=["0"],  # o juiz (holístico) escolhe o índice 0 -- resposta A
    )
    a = _bare_agent(llm)

    result = a.run(TASK, step_callback=None)

    assert result == "resposta A"


def test_reflection_recorded_in_tracing_for_dashboard(monkeypatch):
    # taxa de reflection-rewrite no /metrics depende de tracing.record_reflection
    # ser chamado na 1ª avaliação (não nas seguintes, de self-consistency).
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)
    monkeypatch.setattr(agent_mod, "SELF_CONSISTENCY_MAX_ATTEMPTS", 2)
    recorded = []
    monkeypatch.setattr(agent_mod.tracing, "record_reflection", lambda *a: recorded.append(a))
    llm = _ScriptedLLM(
        react_responses=[
            "Thought: pronto.\nFinal Answer: resposta A",
            "Thought: reescrevendo.\nFinal Answer: resposta B",
        ],
        reflect_jsons=[
            '{"score": 3, "issues": [], "hint": ""}',
            '{"score": 2, "issues": [], "hint": ""}',
        ],
        vote_responses=["1"],
    )
    a = _bare_agent(llm)

    a.run(TASK, step_callback=None)

    assert recorded == [(3, 4, False)]  # só a 1ª avaliação, score < threshold -> accepted=False


def test_self_consistency_keeps_second_answer_when_vote_picks_it(monkeypatch):
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)
    monkeypatch.setattr(agent_mod, "SELF_CONSISTENCY_MAX_ATTEMPTS", 2)
    llm = _ScriptedLLM(
        react_responses=[
            "Thought: pronto.\nFinal Answer: resposta A fraca",
            "Thought: reescrevendo.\nFinal Answer: resposta B, bem melhor",
        ],
        reflect_jsons=[
            '{"score": 2, "issues": ["ruim"], "hint": "melhore"}',
            '{"score": 5, "issues": [], "hint": ""}',
        ],
        vote_responses=["1"],  # juiz escolhe a 2ª -- consistente com o score bem maior
    )
    a = _bare_agent(llm)

    result = a.run(TASK, step_callback=None)

    assert result == "resposta B, bem melhor"


def test_vote_overrides_naive_max_score_pick(monkeypatch):
    """Prova que é voto de verdade (julgamento holístico), não só argmax dos
    scores do critic calculados isoladamente: candidato 1 tem score MENOR que
    o candidato 0, mas o juiz escolhe o candidato 1 mesmo assim."""
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)
    monkeypatch.setattr(agent_mod, "SELF_CONSISTENCY_MAX_ATTEMPTS", 2)
    llm = _ScriptedLLM(
        react_responses=[
            "Thought: pronto.\nFinal Answer: resposta A (score alto isolado)",
            "Thought: reescrevendo.\nFinal Answer: resposta B (score baixo isolado, mas o juiz prefere)",
        ],
        reflect_jsons=[
            '{"score": 3, "issues": [], "hint": ""}',
            '{"score": 2, "issues": [], "hint": ""}',
        ],
        vote_responses=["1"],  # juiz discorda do argmax (que seria 0)
    )
    a = _bare_agent(llm)

    result = a.run(TASK, step_callback=None)

    assert result == "resposta B (score baixo isolado, mas o juiz prefere)"


def test_self_consistency_votes_among_three_independent_attempts(monkeypatch):
    """Ensemble real: 3 tentativas independentes (não 2), voto decide entre
    todas juntas — o item de roadmap pedia exatamente isso em vez do
    best-of-2 sequencial antigo."""
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)
    monkeypatch.setattr(agent_mod, "SELF_CONSISTENCY_MAX_ATTEMPTS", 3)
    llm = _ScriptedLLM(
        react_responses=[
            "Thought: 1.\nFinal Answer: tentativa 1",
            "Thought: 2.\nFinal Answer: tentativa 2",
            "Thought: 3.\nFinal Answer: tentativa 3, a melhor de verdade",
        ],
        reflect_jsons=[
            '{"score": 2, "issues": [], "hint": ""}',
            '{"score": 2, "issues": [], "hint": ""}',
            '{"score": 3, "issues": [], "hint": ""}',
        ],
        vote_responses=["2"],
    )
    a = _bare_agent(llm)

    result = a.run(TASK, step_callback=None)

    assert result == "tentativa 3, a melhor de verdade"
    assert llm.react_responses == []
    assert llm.reflect_jsons == []


def test_self_consistency_guards_first_answer_against_ignored_tool_error(monkeypatch):
    """Bug real visto ao vivo: schedule_task remove com id inválido erra certo,
    mas o modelo escreve 'removido com sucesso' mesmo assim. _guard_final_answer
    pega isso no caminho normal — mas quando self-consistency escolhe uma
    tentativa antiga (por voto), esse retorno pulava o guard. Trava regressão."""
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)
    monkeypatch.setattr(agent_mod, "SELF_CONSISTENCY_MAX_ATTEMPTS", 2)
    llm = _ScriptedLLM(
        react_responses=[
            'Thought: vou remover.\nAction: schedule_task\nAction Input: {"action": "remove", "id": "xyz"}',
            "Thought: pronto.\nFinal Answer: Tarefa removida com sucesso.",
            "Thought: reescrevendo.\nFinal Answer: Removi a tarefa com sucesso, como pedido.",
        ],
        reflect_jsons=[
            '{"score": 3, "issues": ["nao confirmou"], "hint": "confirme"}',
            '{"score": 2, "issues": [], "hint": ""}',
        ],
        vote_responses=["0"],  # juiz fica com a 1ª tentativa
    )
    class _FakeTool:
        description = "gerencia tarefas agendadas"

    a = _bare_agent(llm)
    a.tools = {"schedule_task": _FakeTool()}
    a._execute_tool = lambda action, action_input: "Erro: id 'xyz' não encontrado."

    result = a.run(TASK, step_callback=None)

    assert result.startswith("⚠️")
    assert "Tarefa removida com sucesso." in result
    assert "id 'xyz' não encontrado" in result


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
    assert llm.vote_responses == []  # 1 único candidato — nunca chama o juiz (sem custo extra à toa)
