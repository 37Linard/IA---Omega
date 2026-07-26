from datetime import datetime, timedelta

import pytest

from knowledge_graph import KnowledgeGraph, empty_graph


@pytest.fixture
def isolated_kg():
    """KnowledgeGraph isolado — dict solto em memória, save_fn no-op. Persistência
    de verdade (agent_memory.json) é coberta em test_memory_index_consistency.py."""
    return KnowledgeGraph(empty_graph(), save_fn=lambda: None)


def _iso_days_ago(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).isoformat()


def test_add_triple_stamps_first_and_last_seen(isolated_kg):
    kg = isolated_kg
    kg.add_triple("Gabriel", "gosta de", "Rust")

    rel = kg._graph["relations"][0]
    assert rel["first_seen"]
    assert rel["last_seen"] == rel["first_seen"]
    assert kg._graph["entities"]["Gabriel"]["last_seen"]


def test_add_triple_updates_last_seen_on_repeat(isolated_kg):
    kg = isolated_kg
    kg.add_triple("Gabriel", "gosta de", "Rust")
    kg._graph["relations"][0]["last_seen"] = _iso_days_ago(10)
    kg._graph["relations"][0]["first_seen"] = _iso_days_ago(10)

    kg.add_triple("Gabriel", "gosta de", "Rust")

    rel = kg._graph["relations"][0]
    assert rel["count"] == 2
    assert rel["last_seen"] > rel["first_seen"]  # last_seen foi atualizado, first_seen não


def test_consolidate_removes_stale_weak_relations(isolated_kg):
    kg = isolated_kg
    kg._graph["relations"] = [
        {"s": "A", "p": "rel", "o": "B", "count": 1, "first_seen": _iso_days_ago(200), "last_seen": _iso_days_ago(200)},
    ]
    kg._graph["entities"] = {
        "A": {"count": 1, "first_seen": _iso_days_ago(200), "last_seen": _iso_days_ago(200)},
        "B": {"count": 1, "first_seen": _iso_days_ago(200), "last_seen": _iso_days_ago(200)},
    }

    result = kg.consolidate(max_age_days=90, min_count=2)

    assert result["removed_relations"] == 1
    assert result["removed_entities"] == 2
    assert kg._graph["relations"] == []
    assert kg._graph["entities"] == {}


def test_consolidate_keeps_stale_but_well_reinforced_relations(isolated_kg):
    kg = isolated_kg
    kg._graph["relations"] = [
        {"s": "A", "p": "rel", "o": "B", "count": 5, "first_seen": _iso_days_ago(200), "last_seen": _iso_days_ago(200)},
    ]
    kg._graph["entities"] = {
        "A": {"count": 5, "first_seen": _iso_days_ago(200), "last_seen": _iso_days_ago(200)},
        "B": {"count": 5, "first_seen": _iso_days_ago(200), "last_seen": _iso_days_ago(200)},
    }

    result = kg.consolidate(max_age_days=90, min_count=2)

    assert result == {"removed_relations": 0, "removed_entities": 0}
    assert len(kg._graph["relations"]) == 1


def test_consolidate_keeps_recent_weak_relations(isolated_kg):
    kg = isolated_kg
    kg.add_triple("A", "rel", "B")  # count=1, last_seen=agora

    result = kg.consolidate(max_age_days=90, min_count=2)

    assert result == {"removed_relations": 0, "removed_entities": 0}


def test_consolidate_never_removes_legacy_relations_without_timestamp(isolated_kg):
    kg = isolated_kg
    kg._graph["relations"] = [{"s": "A", "p": "rel", "o": "B", "count": 1}]  # sem last_seen
    kg._graph["entities"]  = {"A": {"count": 1}, "B": {"count": 1}}

    result = kg.consolidate(max_age_days=90, min_count=2)

    assert result == {"removed_relations": 0, "removed_entities": 0}


def test_consolidate_calls_save_fn_only_when_something_changes():
    calls = []
    kg = KnowledgeGraph(empty_graph(), save_fn=lambda: calls.append(1))
    kg._graph["relations"] = [{"s": "A", "p": "rel", "o": "B", "count": 1}]  # sem last_seen, nunca removido
    kg._graph["entities"]  = {"A": {"count": 1}, "B": {"count": 1}}

    kg.consolidate(max_age_days=90, min_count=2)

    assert calls == []  # nada mudou -> não salva


def test_kg_persists_through_shared_memory_data_and_save_fn():
    """Prova a unificação de verdade: duas instâncias de KnowledgeGraph que
    compartilham o MESMO dict (como Memory.kg faz via self.data) enxergam a
    mutação uma da outra sem round-trip de disco."""
    shared = empty_graph()
    saved  = {"n": 0}

    kg1 = KnowledgeGraph(shared, save_fn=lambda: saved.__setitem__("n", saved["n"] + 1))
    kg1.add_triple("Gabriel", "gosta de", "Rust")

    kg2 = KnowledgeGraph(shared, save_fn=lambda: None)
    assert kg2.stats() == {"entities": 2, "relations": 1}
    assert saved["n"] == 1
