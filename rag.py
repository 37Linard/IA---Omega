import hashlib
import json
import logging
import os
import re

import chromadb

log = logging.getLogger(__name__)

RAG_DIR      = os.path.join(os.path.dirname(__file__), "workspace", "rag_db")
RAG_META     = os.path.join(os.path.dirname(__file__), "workspace", "rag_meta.json")
CHUNK_SIZE   = 500   # chars por chunk
CHUNK_OVERLAP = 100  # sobreposição entre chunks


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text   = re.sub(r"\s+", " ", text).strip()
    chunks = []
    start  = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return [c for c in chunks if len(c.strip()) > 30]


# ---------------------------------------------------------------------------
# RAGIndex — ChromaDB com coleção de chunks de PDF
# ---------------------------------------------------------------------------
class RAGIndex:
    def __init__(self):
        os.makedirs(RAG_DIR, exist_ok=True)
        self._client     = chromadb.PersistentClient(path=RAG_DIR)
        self._collection = self._client.get_or_create_collection(
            "pdf_chunks",
            metadata={"hnsw:space": "cosine"},
        )
        self._meta       = self._load_meta()

    # ------------------------------------------------------------------
    def _load_meta(self) -> dict:
        if os.path.exists(RAG_META):
            try:
                with open(RAG_META, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"docs": {}}

    def _save_meta(self):
        with open(RAG_META, "w", encoding="utf-8") as f:
            json.dump(self._meta, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    def _file_hash(self, path: str) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                h.update(block)
        return h.hexdigest()

    # ------------------------------------------------------------------
    def index_pdf(self, path: str) -> dict:
        """Extrai texto do PDF, chunka e indexa no ChromaDB. Idempotente por hash."""
        import pypdf

        fname = os.path.basename(path)
        fhash = self._file_hash(path)

        # Já indexado e não mudou
        if self._meta["docs"].get(fname, {}).get("hash") == fhash:
            n = self._meta["docs"][fname]["chunks"]
            log.info("RAG: %s já indexado (%d chunks)", fname, n)
            return {"status": "already_indexed", "file": fname, "chunks": n}

        # Remove chunks antigos do mesmo arquivo
        if fname in self._meta["docs"]:
            self._remove_doc(fname)

        # Extrai texto página a página
        chunks_ids  = []
        chunks_docs = []
        chunks_meta = []

        with open(path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                for i, chunk in enumerate(_chunk_text(text)):
                    cid = f"{fname}__p{page_num}__c{i}"
                    chunks_ids.append(cid)
                    chunks_docs.append(chunk)
                    chunks_meta.append({
                        "file":  fname,
                        "page":  page_num + 1,
                        "chunk": i,
                    })

        if not chunks_ids:
            return {"status": "error", "file": fname, "error": "Nenhum texto extraído do PDF"}

        # Indexa em lotes de 100 (limite do ChromaDB)
        batch = 100
        for i in range(0, len(chunks_ids), batch):
            self._collection.upsert(
                ids=chunks_ids[i:i+batch],
                documents=chunks_docs[i:i+batch],
                metadatas=chunks_meta[i:i+batch],
            )

        # Salva metadados
        self._meta["docs"][fname] = {
            "hash":   fhash,
            "path":   path,
            "chunks": len(chunks_ids),
            "pages":  len(reader.pages),
        }
        self._save_meta()
        log.info("RAG: indexado %s — %d chunks", fname, len(chunks_ids))
        return {"status": "indexed", "file": fname, "chunks": len(chunks_ids), "pages": len(reader.pages)}

    # ------------------------------------------------------------------
    def _remove_doc(self, fname: str):
        try:
            existing = self._collection.get(where={"file": fname})
            if existing["ids"]:
                self._collection.delete(ids=existing["ids"])
        except Exception as e:
            log.warning("RAG._remove_doc: %s", e)

    # ------------------------------------------------------------------
    def search(self, query: str, n: int = 5, file_filter: str | None = None) -> list[dict]:
        """Busca semântica nos chunks. Retorna lista de {text, file, page, score}."""
        total = self._collection.count()
        if total == 0:
            return []
        k = min(n, total)

        where = {"file": file_filter} if file_filter else None
        try:
            kwargs = {"query_texts": [query], "n_results": k}
            if where:
                kwargs["where"] = where
            res = self._collection.query(**kwargs)
        except Exception as e:
            log.warning("RAG.search: %s", e)
            return []

        results = []
        docs   = res.get("documents",  [[]])[0]
        metas  = res.get("metadatas",  [[]])[0]
        dists  = res.get("distances",  [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists):
            results.append({
                "text":  doc,
                "file":  meta.get("file", ""),
                "page":  meta.get("page", 0),
                "score": round(max(0.0, 1 - dist), 3),  # cosine dist → similaridade [0,1]
            })
        return results

    # ------------------------------------------------------------------
    def list_docs(self) -> list[dict]:
        return [
            {"file": fname, **info}
            for fname, info in self._meta["docs"].items()
        ]


# ---------------------------------------------------------------------------
# Singleton para reutilização
# ---------------------------------------------------------------------------
_rag_index: RAGIndex | None = None

def get_rag_index() -> RAGIndex:
    global _rag_index
    if _rag_index is None:
        _rag_index = RAGIndex()
    return _rag_index
