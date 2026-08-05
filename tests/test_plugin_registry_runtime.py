"""Registries adicionadas via API/UI ficam só em memória (mesmo padrão do
_runtime_models em orchestrator.py) -- não sobrevivem a restart, não tocam
config.py. list_registry_urls() funde config + runtime sem duplicar."""
import plugin_manager as pm


def test_list_registry_urls_starts_with_config_only(monkeypatch):
    monkeypatch.setattr(pm, "_runtime_registry_urls", [])
    monkeypatch.setattr("config.PLUGIN_REGISTRY_URLS", ["https://a.example/reg.json"])

    assert pm.list_registry_urls() == ["https://a.example/reg.json"]


def test_add_registry_url_appends_to_runtime_list(monkeypatch):
    monkeypatch.setattr(pm, "_runtime_registry_urls", [])
    monkeypatch.setattr("config.PLUGIN_REGISTRY_URLS", [])

    pm.add_registry_url("https://b.example/reg.json")

    assert pm.list_registry_urls() == ["https://b.example/reg.json"]


def test_add_registry_url_does_not_duplicate_config_entry(monkeypatch):
    monkeypatch.setattr(pm, "_runtime_registry_urls", [])
    monkeypatch.setattr("config.PLUGIN_REGISTRY_URLS", ["https://a.example/reg.json"])

    pm.add_registry_url("https://a.example/reg.json")

    assert pm.list_registry_urls() == ["https://a.example/reg.json"]


def test_remove_registry_url_only_removes_runtime_entry(monkeypatch):
    monkeypatch.setattr(pm, "_runtime_registry_urls", ["https://b.example/reg.json"])
    monkeypatch.setattr("config.PLUGIN_REGISTRY_URLS", ["https://a.example/reg.json"])

    pm.remove_registry_url("https://a.example/reg.json")  # veio do config, ignora
    pm.remove_registry_url("https://b.example/reg.json")  # veio do runtime, remove

    assert pm.list_registry_urls() == ["https://a.example/reg.json"]


def test_search_registries_uses_merged_list_by_default(monkeypatch):
    calls = []

    def fake_fetch_registry(url):
        calls.append(url)
        return []

    monkeypatch.setattr(pm, "fetch_registry", fake_fetch_registry)
    monkeypatch.setattr(pm, "_runtime_registry_urls", ["https://runtime.example/reg.json"])
    monkeypatch.setattr("config.PLUGIN_REGISTRY_URLS", ["https://config.example/reg.json"])

    pm.search_registries("qualquer")

    assert calls == ["https://config.example/reg.json", "https://runtime.example/reg.json"]
