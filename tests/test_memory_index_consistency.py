"""Achado real: sessions/facts/episodes tinham 3 pontos de persistência
(agent_memory.json = fonte da verdade, LanceDB = espelho de busca semântica,
knowledge_graph.json = grafo separado). O JSON sempre podava por TTL/cap
(_prune_facts, trim de sessions/episodes em 20/MAX_EPISODES), mas NUNCA
propagava o delete pro LanceDB — o item "esquecido" continuava pesquisável
pra sempre, órfão. Pior: o id usado no upsert era derivado da POSIÇÃO na
lista (ex: "f12_2026-07-23"), que é reaproveitada depois de qualquer
prune/trim — um fato novo podia herdar o id de um fato antigo diferente e
sobrescrever o vetor errado no upsert do LanceDB (merge_insert por id).

Esses testes cobrem o fix: id estável (uuid, não-posicional) + delete
propagado pro índice sempre que o JSON poda/corta."""
from datetime import datetime, timedelta

import memory as memory_mod
from memory import Memory, MAX_EPISODES


class _FakeCollection:
    def __init__(self, count=999):
        self._count = count

    def count(self):
        return self._count


class _SpyIndex:
    def __init__(self, empty_collections=False):
        self._ok = True
        n = 0 if empty_collections else 999
        self._facts = _FakeCollection(n)
        self._sessions = _FakeCollection(n)
        self._episodes = _FakeCollection(n)
        self.added_facts = {}
        self.added_sessions = {}
        self.added_episodes = {}
        self.deleted_facts = []
        self.deleted_sessions = []
        self.deleted_episodes = []

    def add_fact(self, fid, text, created):
        self.added_facts[fid] = text

    def delete_fact(self, fid):
        self.deleted_facts.append(fid)

    def add_session(self, sid, task, result, ts):
        self.added_sessions[sid] = task

    def delete_session(self, sid):
        self.deleted_sessions.append(sid)

    def add_episode(self, eid, summary, ts):
        self.added_episodes[eid] = summary

    def delete_episode(self, eid):
        self.deleted_episodes.append(eid)


class _StubShortTerm:
    def add_message(self, *a, **k):
        pass

    def get_messages(self, sid):
        return []

    def get_context(self, sid):
        return ""

    def clear(self, sid):
        pass


class _StubKG:
    def get_context(self, task):
        return ""


def _bare_memory(empty_collections=False):
    m = Memory.__new__(Memory)
    m.data = {"facts": [], "sessions": [], "episodes": []}
    m.index = _SpyIndex(empty_collections=empty_collections)
    m.short_term = _StubShortTerm()
    m._kg = _StubKG()
    m._save = lambda: None
    m._backup = lambda: None
    m._export_to_obsidian = lambda session, scratchpad: None
    return m


def test_save_fact_over_cap_deletes_oldest_from_index(monkeypatch):
    monkeypatch.setattr(memory_mod, "MAX_FACTS", 3)
    m = _bare_memory()

    for i in range(4):
        m.save_fact(f"fato {i}")

    assert len(m.data["facts"]) == 3
    assert len(m.index.deleted_facts) == 1
    dropped_id = m.index.deleted_facts[0]
    assert m.index.added_facts[dropped_id] == "fato 0"
    # o fato removido do JSON nao pode sobreviver escondido no indice
    surviving_ids = {f["id"] for f in m.data["facts"]}
    assert dropped_id not in surviving_ids


def test_save_fact_ttl_expired_deletes_from_index():
    m = _bare_memory()
    old_ts = (datetime.now() - timedelta(days=40)).isoformat()
    m.data["facts"] = [{"id": "f_old", "text": "fato velho", "created": old_ts}]

    m.save_fact("fato novo")

    assert "f_old" in m.index.deleted_facts
    assert [f["text"] for f in m.data["facts"]] == ["fato novo"]


def test_save_fact_ids_never_collide_across_many_prunes(monkeypatch):
    # esquema antigo (posicional) reaproveitava id depois de todo prune —
    # isso fazia o upsert do LanceDB sobrescrever o vetor de um fato diferente.
    monkeypatch.setattr(memory_mod, "MAX_FACTS", 5)
    m = _bare_memory()

    for i in range(30):
        m.save_fact(f"fato {i}")

    all_added_ids = list(m.index.added_facts.keys())
    assert len(all_added_ids) == len(set(all_added_ids))


def test_save_session_over_cap_deletes_oldest_from_index():
    m = _bare_memory()

    for i in range(21):
        m.save_session(f"tarefa {i}", "resultado", scratchpad=[])

    assert len(m.data["sessions"]) == 20
    assert len(m.index.deleted_sessions) == 1
    dropped_id = m.index.deleted_sessions[0]
    assert m.index.added_sessions[dropped_id] == "tarefa 0"


def test_end_session_over_cap_deletes_oldest_episode_from_index():
    m = _bare_memory()
    m.data["episodes"] = [
        {"id": f"e_old{i}", "session_id": f"old{i}", "timestamp": datetime.now().isoformat(),
         "summary": f"ep {i}", "message_count": 2}
        for i in range(MAX_EPISODES)
    ]
    m.short_term.get_messages = lambda sid: [
        {"role": "user", "content": "tarefa nova"},
        {"role": "assistant", "content": "resultado"},
    ]

    m._end_session("new", llm=None)

    assert len(m.data["episodes"]) == MAX_EPISODES
    assert m.index.deleted_episodes == ["e_old0"]


def test_sync_index_backfills_stable_ids_before_indexing_legacy_fact():
    # fato de formato antigo (dict sem "id"), sync deveria rodar (colecoes vazias)
    m = _bare_memory(empty_collections=True)
    m.data["facts"] = [{"text": "fato legado sem id", "created": datetime.now().isoformat()}]

    m._sync_index()

    assert len(m.index.added_facts) == 1
    fid = next(iter(m.index.added_facts))
    assert fid  # nao pode ser "" -- todo fato legado colidiria no mesmo id no upsert
    assert m.data["facts"][0]["id"] == fid
