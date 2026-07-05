import hashlib
import json
import logging
import os
import pickle
import re

log = logging.getLogger(__name__)

RAG_DIR       = os.path.join(os.path.dirname(__file__), "workspace", "rag_lance_db")
RAG_META      = os.path.join(os.path.dirname(__file__), "workspace", "rag_meta.json")
BM25_CACHE    = os.path.join(os.path.dirname(__file__), "workspace", "bm25_cache.pkl")
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 100
SUPPORTED_EXT = {".pdf", ".txt", ".md", ".docx"}
BM25_ALPHA    = 0.65  # peso para busca semântica (1-α para BM25)


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
# BM25 Index — busca por palavras-chave complementando a busca semântica
# ---------------------------------------------------------------------------
class _BM25Store:
    def __init__(self):
        self.corpus: list[str]  = []
        self.meta:   list[dict] = []
        self._bm25              = None
        self._load()

    def _load(self):
        if os.path.exists(BM25_CACHE):
            try:
                with open(BM25_CACHE, "rb") as f:
                    data = pickle.load(f)
                self.corpus = data.get("corpus", [])
                self.meta   = data.get("meta", [])
                self._build()
            except Exception:
                pass

    def _build(self):
        if self.corpus:
            try:
                from rank_bm25 import BM25Okapi
                self._bm25 = BM25Okapi([doc.lower().split() for doc in self.corpus])
            except ImportError:
                pass

    def _save(self):
        os.makedirs(os.path.dirname(BM25_CACHE), exist_ok=True)
        with open(BM25_CACHE, "wb") as f:
            pickle.dump({"corpus": self.corpus, "meta": self.meta}, f)

    def add(self, docs: list[str], metas: list[dict]):
        self.corpus.extend(docs)
        self.meta.extend(metas)
        self._build()
        self._save()

    def remove_file(self, fname: str):
        pairs = [(d, m) for d, m in zip(self.corpus, self.meta) if m.get("file") != fname]
        if pairs:
            self.corpus, self.meta = map(list, zip(*pairs))
        else:
            self.corpus, self.meta = [], []
        self._bm25 = None
        if self.corpus:
            self._build()
        self._save()

    def search(self, query: str, n: int = 10) -> list[tuple[str, dict, float]]:
        if not self._bm25 or not self.corpus:
            return []
        scores = self._bm25.get_scores(query.lower().split())
        max_s  = max(scores) if len(scores) > 0 else 1.0
        if max_s == 0:
            return []
        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:n]
        return [(self.corpus[i], self.meta[i], float(s / max_s)) for i, s in indexed if s > 0]


# ---------------------------------------------------------------------------
# RAGIndex — LanceDB (serverless) com coleção de chunks de documentos
# ---------------------------------------------------------------------------
class RAGIndex:
    def __init__(self):
        os.makedirs(RAG_DIR, exist_ok=True)
        self._ok       = False
        self._embed_fn = None
        try:
            import vector_store
            from embeddings import get_embedder
            self._embed_fn, dim, kind = get_embedder()
            db = vector_store.connect(RAG_DIR)
            self._collection = vector_store.LanceCollection(db, "pdf_chunks", dim)
            self._ok = True
            log.info("RAG: LanceDB OK em %s (embeddings=%s, dim=%d)", RAG_DIR, kind, dim)
        except Exception as e:
            log.warning("RAG: LanceDB indisponível — busca semântica desativada, só BM25. %s", e)
        self._meta = self._load_meta()
        self._bm25 = _BM25Store()

    # ------------------------------------------------------------------
    def _upsert_chunks(self, ids: list[str], docs: list[str], metas: list[dict]):
        if not self._ok:
            return
        batch = 100
        for i in range(0, len(ids), batch):
            batch_docs = docs[i:i + batch]
            vectors = self._embed_fn(batch_docs)
            self._collection.upsert(
                ids=ids[i:i + batch],
                vectors=vectors,
                documents=batch_docs,
                metadatas=metas[i:i + batch],
            )

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

        self._upsert_chunks(chunks_ids, chunks_docs, chunks_meta)
        self._bm25.add(chunks_docs, chunks_meta)
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
        if self._ok:
            try:
                self._collection.delete_by_file(fname)
            except Exception as e:
                log.warning("RAG._remove_doc: %s", e)
        self._bm25.remove_file(fname)

    # ------------------------------------------------------------------
    def search(self, query: str, n: int = 5, file_filter: str | None = None) -> list[dict]:
        """Busca híbrida: semântica (LanceDB) + palavras-chave (BM25).
        Se o índice semântico estiver indisponível, degrada pra BM25-only
        em vez de retornar vazio."""
        semantic_map: dict[str, dict] = {}

        if self._ok:
            total = self._collection.count()
            if total > 0:
                k = min(n * 2, total)
                try:
                    vec = self._embed_fn([query])[0]
                    hits = self._collection.query(vec, k, file=file_filter)
                    for h in hits:
                        meta = h["metadata"]
                        dist = h["distance"] or 0.0
                        sem_score = round(max(0.0, 1 - dist), 4)
                        semantic_map[h["document"]] = {
                            "text":     h["document"],
                            "file":     meta.get("file", ""),
                            "page":     meta.get("page", 0),
                            "semantic": sem_score,
                            "bm25":     0.0,
                        }
                except Exception as e:
                    log.warning("RAG.search semantic: %s", e)

        k = n * 2

        # ── BM25 search ──
        for text, meta, bm25_score in self._bm25.search(query, n=k):
            if file_filter and meta.get("file") != file_filter:
                continue
            if text in semantic_map:
                semantic_map[text]["bm25"] = bm25_score
            else:
                semantic_map[text] = {
                    "text": text,
                    "file": meta.get("file", ""),
                    "page": meta.get("page", 0),
                    "semantic": 0.0,
                    "bm25": bm25_score,
                }

        # ── Hybrid score ──
        combined = []
        for item in semantic_map.values():
            item["score"] = round(BM25_ALPHA * item["semantic"] + (1 - BM25_ALPHA) * item["bm25"], 3)
            combined.append(item)

        combined.sort(key=lambda x: x["score"], reverse=True)
        return [{"text": r["text"], "file": r["file"], "page": r["page"], "score": r["score"]} for r in combined[:n]]

    # ------------------------------------------------------------------
    def index_txt(self, path: str) -> dict:
        """Indexa arquivo de texto plano (.txt ou .md). Idempotente por hash."""
        fname = os.path.basename(path)
        fhash = self._file_hash(path)

        if self._meta["docs"].get(fname, {}).get("hash") == fhash:
            n = self._meta["docs"][fname]["chunks"]
            return {"status": "already_indexed", "file": fname, "chunks": n}

        if fname in self._meta["docs"]:
            self._remove_doc(fname)

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

        chunks_list = _chunk_text(text)
        if not chunks_list:
            return {"status": "error", "file": fname, "error": "Arquivo vazio ou sem texto válido"}

        chunk_ids  = [f"{fname}__c{i}" for i in range(len(chunks_list))]
        chunk_meta = [{"file": fname, "page": 1, "chunk": i} for i in range(len(chunks_list))]

        self._upsert_chunks(chunk_ids, chunks_list, chunk_meta)
        self._bm25.add(chunks_list, chunk_meta)
        self._meta["docs"][fname] = {"hash": fhash, "path": path, "chunks": len(chunk_ids), "pages": 1}
        self._save_meta()
        log.info("RAG: indexado %s — %d chunks", fname, len(chunk_ids))
        return {"status": "indexed", "file": fname, "chunks": len(chunk_ids)}

    # ------------------------------------------------------------------
    def index_docx(self, path: str) -> dict:
        """Indexa arquivo Word .docx. Idempotente por hash."""
        try:
            import docx as _docx
        except ImportError:
            return {"status": "error", "file": os.path.basename(path), "error": "python-docx não instalado. Execute: pip install python-docx"}

        fname = os.path.basename(path)
        fhash = self._file_hash(path)

        if self._meta["docs"].get(fname, {}).get("hash") == fhash:
            n = self._meta["docs"][fname]["chunks"]
            return {"status": "already_indexed", "file": fname, "chunks": n}

        if fname in self._meta["docs"]:
            self._remove_doc(fname)

        doc  = _docx.Document(path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

        chunks_list = _chunk_text(text)
        if not chunks_list:
            return {"status": "error", "file": fname, "error": "Documento vazio"}

        chunk_ids  = [f"{fname}__c{i}" for i in range(len(chunks_list))]
        chunk_meta = [{"file": fname, "page": 1, "chunk": i} for i in range(len(chunks_list))]

        self._upsert_chunks(chunk_ids, chunks_list, chunk_meta)
        self._bm25.add(chunks_list, chunk_meta)
        self._meta["docs"][fname] = {"hash": fhash, "path": path, "chunks": len(chunk_ids), "pages": 1}
        self._save_meta()
        return {"status": "indexed", "file": fname, "chunks": len(chunk_ids)}

    # ------------------------------------------------------------------
    def index_file(self, path: str) -> dict:
        """Indexa arquivo pelo tipo detectado pela extensão."""
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            return self.index_pdf(path)
        elif ext in (".txt", ".md"):
            return self.index_txt(path)
        elif ext == ".docx":
            return self.index_docx(path)
        else:
            return {"status": "error", "file": os.path.basename(path), "error": f"Tipo não suportado: {ext}. Suportados: {SUPPORTED_EXT}"}

    # ------------------------------------------------------------------
    def index_folder(self, folder: str, recursive: bool = False) -> list[dict]:
        """Indexa todos os arquivos suportados em uma pasta."""
        if not os.path.isdir(folder):
            return [{"status": "error", "file": folder, "error": "Pasta não encontrada"}]

        results = []
        walk = os.walk(folder) if recursive else [(folder, [], os.listdir(folder))]
        for dirpath, _, filenames in walk:
            for fname in sorted(filenames):
                ext = os.path.splitext(fname)[1].lower()
                if ext not in SUPPORTED_EXT:
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    result = self.index_file(fpath)
                except Exception as e:
                    result = {"status": "error", "file": fname, "error": str(e)}
                results.append(result)

        if not results:
            return [{"status": "empty", "file": folder, "error": f"Nenhum arquivo suportado encontrado ({', '.join(SUPPORTED_EXT)})"}]
        return results

    # ------------------------------------------------------------------
    def delete_doc(self, fname: str) -> dict:
        """Remove documento do índice."""
        if fname not in self._meta["docs"]:
            return {"status": "error", "error": f"'{fname}' não encontrado no índice"}
        self._remove_doc(fname)
        del self._meta["docs"][fname]
        self._save_meta()
        return {"status": "deleted", "file": fname}

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
