"""Streaming de tool-call parcial — antes só a Final Answer streamava pra UI
(final_stream_start/final_token); Action (nome da tool) e Action Input (JSON
dos argumentos) só viravam evento estruturado depois da resposta INTEIRA
terminar de gerar. Agora _make_streaming_cb emite action_start assim que o
nome da tool aparece e action_input_token conforme o JSON é digitado —
puramente de exibição, a execução real da tool continua esperando o parse
completo (inalterado, ver run() em agent.py)."""
from agent import ReActAgent


def _feed(cb, text):
    """Simula token-a-token (pior caso real: LLM entrega 1 char por vez)."""
    for ch in text:
        cb(ch)


def _make(events):
    a = ReActAgent.__new__(ReActAgent)
    cb, final_started, action_started = a._make_streaming_cb(lambda e: events.append(e))
    return cb, final_started, action_started


def test_plain_thought_streams_as_generic_token():
    events: list = []
    cb, final_started, action_started = _make(events)

    _feed(cb, "Thought: preciso pensar mais um pouco antes de decidir\n")

    assert all(e["type"] == "token" for e in events)
    assert final_started[0] is False
    assert action_started[0] is False


def test_final_answer_streams_to_final_box_not_action():
    events: list = []
    cb, final_started, action_started = _make(events)

    _feed(cb, "Thought: pronto.\nFinal Answer: a resposta é 42")

    assert final_started[0] is True
    assert action_started[0] is False
    kinds = [e["type"] for e in events]
    assert "final_stream_start" in kinds
    assert "action_start" not in kinds
    final_text = "".join(e["content"] for e in events if e["type"] == "final_token")
    assert final_text.strip() == "a resposta é 42"


def test_action_name_streams_as_soon_as_line_completes():
    events: list = []
    cb, final_started, action_started = _make(events)

    _feed(cb, "Thought: vou usar uma ferramenta.\nAction: get_crypto\n")

    assert action_started[0] is True
    assert final_started[0] is False
    action_start_events = [e for e in events if e["type"] == "action_start"]
    assert len(action_start_events) == 1
    assert action_start_events[0]["content"] == "get_crypto"


def test_action_input_json_streams_incrementally_after_marker():
    events: list = []
    cb, final_started, action_started = _make(events)

    _feed(cb, 'Thought: ok.\nAction: get_crypto\nAction Input: {"symbol": "bitcoin"}')

    kinds = [e["type"] for e in events]
    assert "action_input_start" in kinds
    input_text = "".join(
        e["content"] for e in events if e["type"] in ("action_input_start", "action_input_token")
    )
    assert input_text.strip() == '{"symbol": "bitcoin"}'
    # o VALOR do JSON não vaza como "token" genérico de pensamento (o rótulo
    # "Action Input:" em si vaza char-a-char até ser reconhecido por inteiro —
    # mesma limitação pré-existente da detecção de "Final Answer:", não é
    # regressão desse fix)
    generic_tokens = "".join(e["content"] for e in events if e["type"] == "token")
    assert "bitcoin" not in generic_tokens


def test_action_start_fires_only_once_even_with_char_by_char_feed():
    events: list = []
    cb, final_started, action_started = _make(events)

    _feed(cb, 'Action: write_file\nAction Input: {"path": "a.txt", "content": "oi"}')

    assert len([e for e in events if e["type"] == "action_start"]) == 1
    assert len([e for e in events if e["type"] == "action_input_start"]) == 1


def test_final_answer_wins_when_action_word_appears_after_it():
    """Guarda a mesma precedência que já existia pra Final Answer: se 'Action:'
    aparecer DEPOIS de 'Final Answer:' no texto (ex: resposta explicando o
    formato ReAct), continua sendo tratado como final, não dispara streaming
    de tool-call por engano."""
    events: list = []
    cb, final_started, action_started = _make(events)

    _feed(cb, "Thought: ok.\nFinal Answer: no ReAct você escreve Action: nome_da_tool")

    assert final_started[0] is True
    assert action_started[0] is False
