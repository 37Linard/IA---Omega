import pytest

import config
import orchestrator


@pytest.fixture(autouse=True)
def _clean_runtime_models():
    orchestrator._runtime_models.clear()
    yield
    orchestrator._runtime_models.clear()


def test_disabled_by_default():
    assert config.SPECIALIST_MODELS_ENABLED is False


def test_get_specialist_model_ignores_dict_when_disabled(monkeypatch):
    monkeypatch.setattr(config, "SPECIALIST_MODELS_ENABLED", False)
    monkeypatch.setattr(config, "SPECIALIST_MODELS", {"pesquisador": "llama3.2:3b"})

    assert orchestrator.get_specialist_model("pesquisador") == config.OLLAMA_MODEL


def test_get_specialist_model_ignores_runtime_override_when_disabled(monkeypatch):
    monkeypatch.setattr(config, "SPECIALIST_MODELS_ENABLED", False)
    orchestrator._runtime_models["pesquisador"] = "llama3.2:3b"

    assert orchestrator.get_specialist_model("pesquisador") == config.OLLAMA_MODEL


def test_set_specialist_model_raises_when_disabled(monkeypatch):
    monkeypatch.setattr(config, "SPECIALIST_MODELS_ENABLED", False)

    with pytest.raises(orchestrator.SpecialistModelsDisabledError):
        orchestrator.set_specialist_model("pesquisador", "llama3.2:3b")
    assert "pesquisador" not in orchestrator._runtime_models


def test_enabled_preserves_original_behavior(monkeypatch):
    """Prova que o código tá pronto — quando a flag vira True, funciona
    exatamente como antes de ela existir (config.py -> runtime override -> fallback)."""
    monkeypatch.setattr(config, "SPECIALIST_MODELS_ENABLED", True)
    monkeypatch.setattr(config, "SPECIALIST_MODELS", {"pesquisador": "llama3.2:3b"})

    assert orchestrator.get_specialist_model("pesquisador") == "llama3.2:3b"
    assert orchestrator.get_specialist_model("codigo") == config.OLLAMA_MODEL

    orchestrator.set_specialist_model("pesquisador", "qwen2.5-coder:7b")
    assert orchestrator.get_specialist_model("pesquisador") == "qwen2.5-coder:7b"
