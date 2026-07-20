import pytest


@pytest.fixture(autouse=True)
def _isolate_tracing_db(tmp_path, monkeypatch):
    """OllamaLLM.generate() grava um span em TODA chamada (sucesso ou falha),
    mesmo com requests.post mockado — sem isolar aqui, qualquer teste que
    exercite generate() polui workspace/traces.db de verdade. Autouse pra não
    depender de cada arquivo de teste lembrar de isolar isso individualmente."""
    import tracing
    monkeypatch.setattr(tracing, "TRACE_DB", str(tmp_path / "traces_autouse.db"))
