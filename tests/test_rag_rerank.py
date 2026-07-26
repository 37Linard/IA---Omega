"""RAG re-rank real (cross-encoder, fastembed/ONNX) substituindo o mix fixo
BM25_ALPHA=0.65/0.35 como ranking FINAL — o híbrido semântico+BM25 agora só
gera candidatos (recall amplo), o cross-encoder decide a ordem de verdade."""
import rag as rag_mod
from rag import RAGIndex


class _FakeCollection:
    def __init__(self, count=0):
        self._count = count

    def count(self):
        return self._count

    def query(self, vec, k, file=None):
        return []


class _FakeBM25:
    def __init__(self, hits):
        self._hits = hits  # list[(text, meta, score)]

    def search(self, query, n=10):
        return self._hits[:n]


def _bare_index(bm25_hits):
    idx = RAGIndex.__new__(RAGIndex)
    idx._ok = False  # sem LanceDB — so BM25 gera candidatos, mais simples de controlar no teste
    idx._embed_fn = lambda texts: [[0.0]] * len(texts)
    idx._collection = _FakeCollection(count=0)
    idx._bm25 = _FakeBM25(bm25_hits)
    idx._meta = {"docs": {}}
    return idx


class _StubReranker:
    def __init__(self, score_map):
        self.score_map = score_map
        self.calls = []

    def rerank(self, query, documents):
        docs = list(documents)
        self.calls.append((query, docs))
        return [self.score_map[d] for d in docs]


_WEAK_BM25   = "doc fraco no bm25 mas o cross-encoder acha o melhor"
_STRONG_BM25 = "doc forte no bm25 mas irrelevante de verdade"


def test_search_uses_cross_encoder_score_to_reorder(monkeypatch):
    hits = [
        (_WEAK_BM25,   {"file": "a.pdf", "page": 1}, 0.3),
        (_STRONG_BM25, {"file": "b.pdf", "page": 1}, 0.9),
    ]
    idx = _bare_index(hits)
    stub = _StubReranker({_WEAK_BM25: 0.95, _STRONG_BM25: 0.10})
    monkeypatch.setattr(rag_mod, "_get_reranker", lambda: stub)

    results = idx.search("pergunta", n=2)

    # BM25 sozinho colocaria _STRONG_BM25 primeiro — cross-encoder inverte
    assert [r["text"] for r in results] == [_WEAK_BM25, _STRONG_BM25]
    assert results[0]["score"] == 0.95
    assert stub.calls  # o reranker foi de fato chamado com os candidatos


def test_search_keeps_hybrid_order_when_reranker_unavailable(monkeypatch):
    hits = [
        (_WEAK_BM25,   {"file": "a.pdf", "page": 1}, 0.3),
        (_STRONG_BM25, {"file": "b.pdf", "page": 1}, 0.9),
    ]
    idx = _bare_index(hits)
    monkeypatch.setattr(rag_mod, "_get_reranker", lambda: None)

    results = idx.search("pergunta", n=2)

    assert [r["text"] for r in results] == [_STRONG_BM25, _WEAK_BM25]


def test_search_keeps_hybrid_order_when_reranker_raises(monkeypatch):
    hits = [
        (_WEAK_BM25,   {"file": "a.pdf", "page": 1}, 0.3),
        (_STRONG_BM25, {"file": "b.pdf", "page": 1}, 0.9),
    ]
    idx = _bare_index(hits)

    class _Boom:
        def rerank(self, query, documents):
            raise RuntimeError("modelo quebrou")

    monkeypatch.setattr(rag_mod, "_get_reranker", lambda: _Boom())

    results = idx.search("pergunta", n=2)

    assert [r["text"] for r in results] == [_STRONG_BM25, _WEAK_BM25]


def test_get_reranker_caches_failure_and_does_not_retry(monkeypatch):
    monkeypatch.setattr(rag_mod, "_reranker", None)
    monkeypatch.setattr(rag_mod, "_reranker_failed", False)
    calls = {"n": 0}

    class _Boom:
        def __init__(self, model_name):
            calls["n"] += 1
            raise RuntimeError("sem internet pra baixar modelo")

    monkeypatch.setattr("fastembed.rerank.cross_encoder.TextCrossEncoder", _Boom)

    r1 = rag_mod._get_reranker()
    r2 = rag_mod._get_reranker()

    assert r1 is None and r2 is None
    assert calls["n"] == 1  # 2ª chamada nao tenta de novo -- falha fica cacheada
