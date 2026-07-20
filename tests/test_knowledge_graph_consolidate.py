from datetime import datetime, timedelta

import pytest

import knowledge_graph as kg_mod
from knowledge_graph import KnowledgeGraph


@pytest.fixture
def isolated_kg(tmp_path, monkeypatch):
    """KnowledgeGraph isolado — nunca toca workspace/knowledge_graph.json real."""
    monkeypatch.setattr(kg_mod, "GRAPH_FILE", str(tmp_path / "knowledge_graph.json"))
    return KnowledgeGraph()


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


def test_consolidate_persists_changes_to_disk(isolated_kg):
    kg = isolated_kg
    kg._graph["relations"] = [
        {"s": "A", "p": "rel", "o": "B", "count": 1, "first_seen": _iso_days_ago(200), "last_seen": _iso_days_ago(200)},
    ]
    kg._graph["entities"] = {"A": {"count": 1}, "B": {"count": 1}}

    kg.consolidate(max_age_days=90, min_count=2)

    reloaded = KnowledgeGraph()
    assert reloaded._graph["relations"] == []
