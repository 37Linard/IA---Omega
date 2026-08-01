import config


def test_primary_model_and_ensemble_first_slot_match():
    """ENSEMBLE_MODELS[0] eh string literal, nao referencia OLLAMA_MODEL —
    trocar o principal sem atualizar este slot deixa o self-consistency
    votando entre o modelo novo e uma versao desatualizada do antigo."""
    assert config.ENSEMBLE_MODELS[0] == config.OLLAMA_MODEL


def test_fallback_model_never_in_ensemble_pool():
    if config.FALLBACK_MODEL:
        assert config.FALLBACK_MODEL not in config.ENSEMBLE_MODELS
