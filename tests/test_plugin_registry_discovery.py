"""Descoberta (marketplace) — registry é só um índice JSON pesquisável
(name/description/tags -> manifest_url). Nunca instala nada sozinho: achar
um manifest_url aqui não pula hash nem assinatura (ver
test_plugin_manager_signature.py) — search/registry-list são puramente
informativos."""
import json

import requests

import plugin_manager as pm


REGISTRY = [
    {"name": "clima_tool", "description": "Consulta previsão do tempo",
     "author_id": "autor1", "manifest_url": "https://example.com/clima/manifest.json",
     "tags": ["clima", "previsao"]},
    {"name": "crypto_alerta", "description": "Alerta de preço de criptomoeda",
     "author_id": "autor2", "manifest_url": "https://example.com/crypto/manifest.json",
     "tags": ["bitcoin", "cripto"]},
]


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_fetch_registry_from_local_file(tmp_path):
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(REGISTRY), encoding="utf-8")

    entries = pm.fetch_registry(str(reg_path))

    assert len(entries) == 2
    assert entries[0]["name"] == "clima_tool"


def test_fetch_registry_from_url(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda url, timeout=None: _FakeResponse(REGISTRY))

    entries = pm.fetch_registry("https://example.com/registry.json")

    assert len(entries) == 2


def test_fetch_registry_skips_malformed_entries_without_crashing(tmp_path):
    mixed = REGISTRY + [{"name": "incompleto"}]  # falta description/manifest_url
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(mixed), encoding="utf-8")

    entries = pm.fetch_registry(str(reg_path))

    assert len(entries) == 2  # a entrada incompleta foi pulada, nao quebrou tudo


def test_fetch_registry_rejects_non_list_payload(tmp_path):
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

    try:
        pm.fetch_registry(str(reg_path))
        assert False, "deveria ter rejeitado payload que nao e lista"
    except pm.PluginError:
        pass


def test_search_registries_matches_by_tag(tmp_path):
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(REGISTRY), encoding="utf-8")

    hits = pm.search_registries("bitcoin", registry_urls=[str(reg_path)])

    assert len(hits) == 1
    assert hits[0]["name"] == "crypto_alerta"


def test_search_registries_empty_query_lists_everything(tmp_path):
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(REGISTRY), encoding="utf-8")

    hits = pm.search_registries("", registry_urls=[str(reg_path)])

    assert len(hits) == 2


def test_search_registries_skips_unreachable_registry_without_failing_others(tmp_path):
    good_path = tmp_path / "good.json"
    good_path.write_text(json.dumps(REGISTRY), encoding="utf-8")
    broken_path = str(tmp_path / "does_not_exist.json")

    hits = pm.search_registries("clima", registry_urls=[broken_path, str(good_path)])

    assert len(hits) == 1
    assert hits[0]["name"] == "clima_tool"


def test_search_registries_uses_config_urls_by_default(monkeypatch, tmp_path):
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(REGISTRY), encoding="utf-8")
    monkeypatch.setattr("config.PLUGIN_REGISTRY_URLS", [str(reg_path)])

    hits = pm.search_registries("clima")

    assert len(hits) == 1
