"""Regressão: visto ao vivo — schedule_task remove com id inválido, a tool
recusou certo ("Erro: nenhuma tarefa..."), mas o Final Answer do agente disse
"removido com sucesso" mesmo assim. _guard_final_answer detecta esse tipo de
descompasso de forma determinística (sem depender do LLM se autocorrigir)."""
from agent import ReActAgent


def _bare_agent(scratchpad):
    a = ReActAgent.__new__(ReActAgent)
    a.scratchpad = scratchpad
    return a


def test_guard_prepends_warning_when_final_answer_ignores_tool_error():
    a = _bare_agent(["Observation: Erro: nenhuma tarefa agendada com id 'xyz'."])

    result = a._guard_final_answer("A tarefa foi removida com sucesso!")

    assert result.startswith("⚠️")
    assert "removida com sucesso" in result  # texto original preservado, só com aviso na frente


def test_guard_leaves_final_answer_untouched_when_it_acknowledges_the_error():
    a = _bare_agent(["Observation: Erro: nenhuma tarefa agendada com id 'xyz'."])

    result = a._guard_final_answer("Não consegui remover — esse id não existe.")

    assert result == "Não consegui remover — esse id não existe."


def test_guard_leaves_final_answer_untouched_when_last_observation_ok():
    a = _bare_agent(["Observation: Tarefa agendada com sucesso: todo dia às 09:00."])

    result = a._guard_final_answer("Perfeito! Agendei pra você.")

    assert result == "Perfeito! Agendei pra você."


def test_guard_ignores_when_scratchpad_has_no_observation():
    a = _bare_agent(["Thought: só raciocínio, nenhuma tool rodou ainda."])

    result = a._guard_final_answer("Resposta qualquer.")

    assert result == "Resposta qualquer."


def test_guard_looks_at_most_recent_observation_only():
    a = _bare_agent([
        "Observation: Erro: falha na primeira tentativa.",
        "Observation: Tarefa agendada com sucesso: todo dia às 09:00.",
    ])

    result = a._guard_final_answer("Perfeito! Agendei pra você.")

    assert result == "Perfeito! Agendei pra você."  # erro foi da tentativa anterior, já corrigida


def test_guard_emits_error_step_when_warning_triggers():
    a = _bare_agent(["Observation: Erro: nenhuma tarefa agendada com id 'xyz'."])
    emitted = []

    a._guard_final_answer("Removido com sucesso!", emit=emitted.append)

    assert len(emitted) == 1
    assert emitted[0]["type"] == "error"
    assert "xyz" in emitted[0]["content"]


def test_guard_does_not_emit_when_no_mismatch():
    a = _bare_agent(["Observation: Tudo certo."])
    emitted = []

    a._guard_final_answer("Perfeito!", emit=emitted.append)

    assert emitted == []


def test_last_observation_returns_most_recent():
    a = _bare_agent(["Observation: primeira", "Thought: algo", "Observation: segunda"])
    assert a._last_observation() == "segunda"


def test_last_observation_empty_when_none_present():
    a = _bare_agent(["Thought: só isso"])
    assert a._last_observation() == ""
