from datetime import datetime, timedelta

from memory import Memory, EPISODE_MIN_MSGS, MAX_EPISODES


class _StubShortTerm:
    def __init__(self):
        self._msgs: dict[str, list] = {}

    def add_message(self, session_id, role, content):
        self._msgs.setdefault(session_id, []).append({"role": role, "content": content})

    def get_messages(self, session_id):
        return self._msgs.get(session_id, [])

    def get_context(self, session_id):
        return ""

    def clear(self, session_id):
        self._msgs.pop(session_id, None)


class _StubIndex:
    _ok = False

    def add_episode(self, eid, summary, timestamp):
        pass


class _StubKG:
    def get_context(self, task):
        return ""


class _StubLLM:
    def __init__(self, reply="resumo gerado pelo llm"):
        self.reply = reply
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        return self.reply


def _bare_memory():
    m = Memory.__new__(Memory)
    m.data = {"facts": [], "sessions": [], "episodes": []}
    m.short_term = _StubShortTerm()
    m.index = _StubIndex()
    m._kg = _StubKG()
    m._save = lambda: None  # não bate em disco no teste
    return m


def test_end_session_ignores_too_short_session():
    m = _bare_memory()
    m.short_term.add_message("s1", "user", "oi")

    m._end_session("s1", llm=_StubLLM())

    assert m.data["episodes"] == []


def test_end_session_summarizes_with_llm_and_clears_short_term():
    m = _bare_memory()
    m.short_term.add_message("s1", "user", "pesquisa sobre bitcoin")
    m.short_term.add_message("s1", "assistant", "preço atual é X")
    llm = _StubLLM(reply="usuário pediu preço do bitcoin, agente respondeu")

    m._end_session("s1", llm=llm)

    assert llm.calls == 1
    assert len(m.data["episodes"]) == 1
    ep = m.data["episodes"][0]
    assert ep["session_id"] == "s1"
    assert ep["summary"] == "usuário pediu preço do bitcoin, agente respondeu"
    assert ep["message_count"] == 2
    assert m.short_term.get_messages("s1") == []  # limpo após resumir


def test_end_session_without_llm_falls_back_to_first_user_message():
    m = _bare_memory()
    m.short_term.add_message("s1", "user", "cria um arquivo teste.txt")
    m.short_term.add_message("s1", "assistant", "feito")

    m._end_session("s1", llm=None)

    assert len(m.data["episodes"]) == 1
    assert m.data["episodes"][0]["summary"] == "cria um arquivo teste.txt"


def test_episodes_list_capped_at_max():
    m = _bare_memory()
    m.data["episodes"] = [
        {"session_id": f"old{i}", "timestamp": datetime.now().isoformat(),
         "summary": f"ep {i}", "message_count": 2}
        for i in range(MAX_EPISODES)
    ]
    m.short_term.add_message("new", "user", "tarefa nova")
    m.short_term.add_message("new", "assistant", "resultado")

    m._end_session("new", llm=None)

    assert len(m.data["episodes"]) == MAX_EPISODES
    assert m.data["episodes"][-1]["session_id"] == "new"
    assert m.data["episodes"][0]["session_id"] == "old1"  # o mais antigo caiu fora


def test_get_last_episode_context_excludes_current_session_and_formats_recency():
    m = _bare_memory()
    ts = (datetime.now() - timedelta(hours=2)).isoformat()
    m.data["episodes"] = [{"session_id": "s1", "timestamp": ts,
                            "summary": "você pediu ajuda com X", "message_count": 3}]

    ctx = m.get_last_episode_context(exclude_session_id="s2")

    assert "você pediu ajuda com X" in ctx
    assert "há 2h" in ctx


def test_get_last_episode_context_excludes_own_session():
    m = _bare_memory()
    m.data["episodes"] = [{"session_id": "s1", "timestamp": datetime.now().isoformat(),
                            "summary": "resumo", "message_count": 2}]

    ctx = m.get_last_episode_context(exclude_session_id="s1")

    assert ctx == ""


def test_search_episodes_falls_back_to_keyword_match_without_lancedb():
    m = _bare_memory()
    m.data["episodes"] = [
        {"session_id": "s1", "timestamp": datetime.now().isoformat(),
         "summary": "usuário pediu preço do bitcoin", "message_count": 2},
        {"session_id": "s2", "timestamp": datetime.now().isoformat(),
         "summary": "usuário criou arquivo teste.txt", "message_count": 2},
    ]

    hits = m.search_episodes("BITCOIN", n=3)

    assert len(hits) == 1
    assert hits[0]["summary"] == "usuário pediu preço do bitcoin"


def test_search_episodes_returns_most_recent_first_on_fallback():
    m = _bare_memory()
    m.data["episodes"] = [
        {"session_id": "s1", "timestamp": datetime.now().isoformat(),
         "summary": "tarefa X antiga", "message_count": 2},
        {"session_id": "s2", "timestamp": datetime.now().isoformat(),
         "summary": "tarefa X recente", "message_count": 2},
    ]

    hits = m.search_episodes("tarefa X", n=1)

    assert len(hits) == 1
    assert hits[0]["summary"] == "tarefa X recente"


def test_get_context_injects_recall_only_on_first_message_of_new_session():
    m = _bare_memory()
    m.data["episodes"] = [{"session_id": "old", "timestamp": datetime.now().isoformat(),
                            "summary": "resumo da sessão passada", "message_count": 2}]

    fresh_ctx = m.get_context(task="", session_id="new")
    assert "resumo da sessão passada" in fresh_ctx

    m.short_term.add_message("new", "user", "primeira mensagem")
    ongoing_ctx = m.get_context(task="", session_id="new")
    assert "resumo da sessão passada" not in ongoing_ctx
