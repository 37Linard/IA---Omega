"""Regressão: visto ao vivo — modelo pequeno, depois de erros de tool,
tentava "concluir" escrevendo `Action: final_answer` / `Action: echo` (tool
que não existe pra esse propósito) em vez do formato literal
`Final Answer: ...`, esgotando o limite de passos sem nunca responder de
verdade. _parse_response agora reconhece esse padrão e trata como Final
Answer em vez de estourar erro de "ferramenta não existe"."""
from agent import ReActAgent


def _bare_agent(tools=None):
    a = ReActAgent.__new__(ReActAgent)
    a.tools = tools or {}
    return a


def test_final_answer_alias_with_message_key_is_treated_as_final_answer():
    a = _bare_agent()
    response = (
        "Thought: terminei.\n"
        'Action: final_answer\n'
        'Action Input: {"message": "A tarefa não existe."}'
    )

    action, action_input = a._parse_response(response)

    assert action == "Final Answer"
    assert action_input == "A tarefa não existe."


def test_done_alias_with_text_key_is_treated_as_final_answer():
    a = _bare_agent()
    response = 'Action: done\nAction Input: {"text": "Pronto!"}'

    action, action_input = a._parse_response(response)

    assert action == "Final Answer"
    assert action_input == "Pronto!"


def test_real_tool_named_like_alias_is_not_intercepted():
    # se um dia existir uma tool real chamada "answer", ela deve continuar
    # funcionando normalmente — o fallback só age quando a tool NÃO existe
    a = _bare_agent(tools={"answer": object()})
    response = 'Action: answer\nAction Input: {"message": "oi"}'

    action, action_input = a._parse_response(response)

    assert action == "answer"  # tratado como tool de verdade, não como Final Answer
    assert action_input == {"message": "oi"}


def test_unrelated_nonexistent_tool_still_raises():
    a = _bare_agent()
    response = 'Action: ferramenta_que_nao_existe\nAction Input: {"x": "y"}'

    try:
        a._parse_response(response)
        assert False, "deveria ter levantado ValueError"
    except ValueError as e:
        assert "não existe" in str(e)


def test_final_answer_alias_falls_back_to_any_string_value_in_dict():
    # chave que não previmos ('foo') ainda funciona — pega o primeiro valor string
    a = _bare_agent()
    response = 'Action: final_answer\nAction Input: {"foo": "bar"}'

    action, action_input = a._parse_response(response)

    assert action == "Final Answer"
    assert action_input == "bar"


def test_final_answer_alias_without_any_usable_text_falls_through_to_error():
    a = _bare_agent()
    response = 'Action: final_answer\nAction Input: {"count": 5}'

    try:
        a._parse_response(response)
        assert False, "deveria ter levantado ValueError (sem texto aproveitável)"
    except ValueError as e:
        assert "não existe" in str(e)


def test_final_answer_alias_matches_with_surrounding_noise():
    # modelo às vezes escreve algo tipo "final_answer_tool" ou com formatação extra
    a = _bare_agent()
    response = 'Action: final_answer_tool\nAction Input: {"message": "Pronto!"}'

    action, action_input = a._parse_response(response)

    assert action == "Final Answer"
    assert action_input == "Pronto!"
