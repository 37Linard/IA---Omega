from datetime import datetime, timedelta

import memory as memory_mod
from memory import Memory, MAX_FACTS, CONTEXT_MAX_FACTS, CONTEXT_FACT_CHARS


class _StubShortTerm:
    def get_context(self, session_id):
        return ""


class _StubIndex:
    _ok = False


class _StubKG:
    def get_context(self, task):
        return ""


def _bare_memory(facts=None, sessions=None):
    m = Memory.__new__(Memory)
    m.data = {"facts": facts or [], "sessions": sessions or []}
    m.short_term = _StubShortTerm()
    m.index = _StubIndex()
    m._kg = _StubKG()
    return m


def _fact(text, days_ago=0):
    ts = (datetime.now() - timedelta(days=days_ago)).isoformat()
    return {"text": text, "created": ts}


def test_prune_facts_caps_count_even_when_all_within_ttl():
    m = _bare_memory(facts=[_fact(f"fato {i}", days_ago=1) for i in range(MAX_FACTS + 50)])

    m._prune_facts()

    assert len(m.data["facts"]) == MAX_FACTS
    # mantém os mais recentes (últimos adicionados), não os mais antigos
    assert m.data["facts"][-1]["text"] == f"fato {MAX_FACTS + 49}"


def test_prune_facts_still_drops_by_ttl():
    m = _bare_memory(facts=[_fact("velho", days_ago=40), _fact("novo", days_ago=1)])

    m._prune_facts()

    texts = [f["text"] for f in m.data["facts"]]
    assert texts == ["novo"]


def test_get_context_fallback_caps_facts_injected_into_prompt():
    total = CONTEXT_MAX_FACTS + 10
    facts = [_fact(f"fato numero {i}", days_ago=1) for i in range(total)]
    m = _bare_memory(facts=facts)

    ctx = m.get_context(task="", session_id="")

    assert f"{CONTEXT_MAX_FACTS} de {total}" in ctx
    # só os últimos CONTEXT_MAX_FACTS aparecem — os mais antigos não vazam pro prompt
    assert "fato numero 0" not in ctx
    assert f"fato numero {total - 1}" in ctx


def test_get_context_truncates_long_fact_text():
    long_text = "x" * 500
    m = _bare_memory(facts=[_fact(long_text, days_ago=1)])

    ctx = m.get_context(task="", session_id="")

    assert long_text not in ctx  # não vaza o texto inteiro
    assert "x" * CONTEXT_FACT_CHARS in ctx


def test_get_context_empty_when_no_data():
    m = _bare_memory()

    ctx = m.get_context(task="", session_id="")

    assert ctx == ""
