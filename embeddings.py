import json
import logging
import os

log = logging.getLogger(__name__)

_EMBEDDER_CONFIG = os.path.join(os.path.dirname(__file__), "workspace", "embedder_config.json")

_embed_fn = None
_dim      = None
_kind     = None


def _load_persisted_kind() -> str | None:
    if os.path.exists(_EMBEDDER_CONFIG):
        try:
            with open(_EMBEDDER_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f).get("kind")
        except Exception:
            pass
    return None


def _persist_kind(kind: str):
    try:
        os.makedirs(os.path.dirname(_EMBEDDER_CONFIG), exist_ok=True)
        with open(_EMBEDDER_CONFIG, "w", encoding="utf-8") as f:
            json.dump({"kind": kind}, f)
    except Exception:
        pass


def _make_ollama():
    from config import EMBED_MODEL, OLLAMA_URL
    from llm import OllamaEmbeddingFunction
    fn = OllamaEmbeddingFunction(EMBED_MODEL, OLLAMA_URL)
    return fn, 768, "ollama"


def _make_fastembed():
    from fastembed import TextEmbedding
    model = TextEmbedding()  # padrão: BAAI/bge-small-en-v1.5, 384-dim, ONNX (sem torch/Ollama)

    def fn(texts: list[str]) -> list[list[float]]:
        return [e.tolist() for e in model.embed(texts)]

    return fn, 384, "fastembed"


def get_embedder():
    """Retorna (func, dim, kind). func: list[str] -> list[list[float]].

    Prioriza Ollama (nomic-embed-text, 768-dim — melhor qualidade em PT-BR)
    se disponível; senão usa fastembed local (ONNX, zero-setup, não depende
    de Ollama nem torch) como fallback.

    O backend escolhido é persistido em workspace/embedder_config.json e
    reutilizado nas próximas execuções — as tabelas do LanceDB têm dimensão
    de vetor fixa, então trocar de embedder no meio do caminho quebraria
    buscas existentes sem reindexar tudo. Se o backend persistido era
    "ollama" mas o serviço está fora do ar, falha alto (em vez de cair
    silenciosamente pro fastembed de 384-dim e corromper a tabela de 768-dim)."""
    global _embed_fn, _dim, _kind
    if _embed_fn is not None:
        return _embed_fn, _dim, _kind

    from config import EMBED_MODEL, OLLAMA_URL
    from llm import OllamaEmbeddingFunction

    persisted = _load_persisted_kind()

    if persisted == "ollama":
        if not OllamaEmbeddingFunction.is_available(EMBED_MODEL, OLLAMA_URL):
            raise RuntimeError(
                f"Embeddings configurados para Ollama ({EMBED_MODEL}) mas o serviço está "
                "indisponível. Inicie o Ollama (ollama serve) ou apague "
                "workspace/embedder_config.json pra trocar de backend "
                "(cuidado: exige reindexar tudo, dimensão do vetor muda)."
            )
        _embed_fn, _dim, _kind = _make_ollama()
    elif persisted == "fastembed":
        _embed_fn, _dim, _kind = _make_fastembed()
    else:
        # primeira vez — decide o backend e persiste a escolha
        if OllamaEmbeddingFunction.is_available(EMBED_MODEL, OLLAMA_URL):
            _embed_fn, _dim, _kind = _make_ollama()
        else:
            _embed_fn, _dim, _kind = _make_fastembed()
        _persist_kind(_kind)

    log.info("Embeddings: backend=%s dim=%d", _kind, _dim)
    return _embed_fn, _dim, _kind
