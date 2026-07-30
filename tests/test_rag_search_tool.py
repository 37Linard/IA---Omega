from tools.rag_search_tool import RagSearchTool


class _FakeRagIndex:
    def __init__(self, docs=None, results=None):
        self._docs    = docs or []
        self._results = results or []

    def list_docs(self):
        return self._docs

    def search(self, query, n=5, file_filter=None):
        return self._results


class _FakeMemory:
    def __init__(self, episodes=None):
        self._episodes = episodes or []

    def search_episodes(self, query, n=3):
        return self._episodes


def _tool(monkeypatch, docs=None, doc_results=None, episodes=None):
    fake_index  = _FakeRagIndex(docs=docs, results=doc_results)
    fake_memory = _FakeMemory(episodes=episodes)
    monkeypatch.setattr("tools.rag_search_tool.get_rag_index", lambda: fake_index)
    monkeypatch.setattr("tools.rag_search_tool.Memory", lambda: fake_memory)
    return RagSearchTool()


def test_requires_query(monkeypatch):
    tool = _tool(monkeypatch)
    result = tool.run({})
    assert "erro" in result.lower()


def test_returns_message_when_nothing_found(monkeypatch):
    tool = _tool(monkeypatch, docs=[], doc_results=[], episodes=[])
    result = tool.run({"query": "bitcoin"})
    assert "nenhum trecho relevante" in result.lower()


def test_includes_doc_results_when_pdfs_indexed(monkeypatch):
    tool = _tool(
        monkeypatch,
        docs=[{"file": "contrato.pdf"}],
        doc_results=[{"file": "contrato.pdf", "page": 2, "score": 0.9, "text": "cláusula de rescisão"}],
        episodes=[],
    )
    result = tool.run({"query": "rescisão"})
    assert "contrato.pdf" in result
    assert "cláusula de rescisão" in result


def test_includes_episode_results_even_without_pdfs(monkeypatch):
    tool = _tool(
        monkeypatch,
        docs=[],
        doc_results=[],
        episodes=[{"summary": "usuário pediu preço do bitcoin", "ts": "2026-07-20"}],
    )
    result = tool.run({"query": "bitcoin"})
    assert "sessão anterior" in result.lower()
    assert "usuário pediu preço do bitcoin" in result


def test_file_filter_disables_episode_search(monkeypatch):
    tool = _tool(
        monkeypatch,
        docs=[{"file": "contrato.pdf"}],
        doc_results=[],
        episodes=[{"summary": "não deveria aparecer", "ts": "2026-07-20"}],
    )
    result = tool.run({"query": "rescisão", "file": "contrato.pdf"})
    assert "não deveria aparecer" not in result


def test_last_sources_populated_for_frontend_citations(monkeypatch):
    """last_sources é o side-channel que agent.py lê pra emitir o evento WS
    rag_sources (fontes/trecho na resposta) — não vai na Observation em
    texto, mas tem que refletir os mesmos resultados."""
    tool = _tool(
        monkeypatch,
        docs=[{"file": "contrato.pdf"}],
        doc_results=[{"file": "contrato.pdf", "page": 2, "score": 0.9, "text": "cláusula de rescisão " * 20}],
        episodes=[],
    )
    tool.run({"query": "rescisão"})

    assert tool.last_sources == [{
        "file": "contrato.pdf", "page": 2, "score": 0.9,
        "excerpt": ("cláusula de rescisão " * 20)[:220],
    }]


def test_last_sources_empty_when_nothing_found(monkeypatch):
    tool = _tool(monkeypatch, docs=[], doc_results=[], episodes=[])
    tool.run({"query": "bitcoin"})
    assert tool.last_sources == []


def test_last_sources_resets_between_calls(monkeypatch):
    """1ª chamada acha resultado, 2ª não — last_sources não pode vazar da
    chamada anterior (bug real de outra classe: side-channel goiaba)."""
    tool = _tool(
        monkeypatch,
        docs=[{"file": "contrato.pdf"}],
        doc_results=[{"file": "contrato.pdf", "page": 1, "score": 0.5, "text": "algo"}],
        episodes=[],
    )
    tool.run({"query": "rescisão"})
    assert tool.last_sources

    monkeypatch.setattr("tools.rag_search_tool.get_rag_index", lambda: _FakeRagIndex(docs=[], results=[]))
    tool.run({"query": "outra coisa"})
    assert tool.last_sources == []
