import json
import logging

import lancedb
import pyarrow as pa

log = logging.getLogger(__name__)


def _escape(s: str) -> str:
    return s.replace("'", "''")


def _table_exists(db: "lancedb.DBConnection", name: str) -> bool:
    # list_tables() em versões recentes retorna um ListTablesResponse (.tables),
    # não uma lista simples — normaliza pros dois formatos.
    names = db.list_tables()
    return name in getattr(names, "tables", names)


class LanceCollection:
    """Wrapper fino sobre uma tabela LanceDB — interface parecida com uma
    collection do ChromaDB (upsert por id, query por vetor + filtro, delete
    por id/filtro, count) pra minimizar mudança nos consumidores
    (VectorIndex em memory.py, RAGIndex em rag.py)."""

    def __init__(self, db: "lancedb.DBConnection", name: str, dim: int):
        self._dim = dim
        if _table_exists(db, name):
            self._table = db.open_table(name)
        else:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), dim)),
                pa.field("document", pa.string()),
                pa.field("metadata", pa.string()),  # JSON — metadata heterogênea entre collections
                # coluna plana pra filtro exato via SQL — extraída de metadata["file"] quando presente
                # (RAGIndex filtra/remove por arquivo; sessions/facts deixam vazio, sem custo real)
                pa.field("file", pa.string()),
            ])
            self._table = db.create_table(name, schema=schema)

    def count(self) -> int:
        return self._table.count_rows()

    def upsert(self, ids: list[str], vectors: list[list[float]], documents: list[str], metadatas: list[dict]):
        rows = [
            {
                "id": i, "vector": v, "document": d,
                "metadata": json.dumps(m, ensure_ascii=False),
                "file": m.get("file", ""),
            }
            for i, v, d, m in zip(ids, vectors, documents, metadatas)
        ]
        (self._table.merge_insert("id")
            .when_matched_update_all()
            .when_not_matched_insert_all()
            .execute(rows))

    def query(self, vector: list[float], k: int, file: str | None = None) -> list[dict]:
        q = self._table.search(vector).metric("cosine").limit(k)
        if file:
            q = q.where(f"file = '{_escape(file)}'")
        return [self._row_to_dict(r) for r in q.to_list()]

    def get(self, where: str) -> list[dict]:
        rows = self._table.search().where(where).to_list()
        return [self._row_to_dict(r) for r in rows]

    def get_by_file(self, fname: str) -> list[dict]:
        return self.get(f"file = '{_escape(fname)}'")

    def delete_by_file(self, fname: str):
        self._table.delete(f"file = '{_escape(fname)}'")

    def delete(self, ids: list[str] | None = None, where: str | None = None):
        if where:
            self._table.delete(where)
        elif ids:
            id_list = ", ".join(f"'{_escape(i)}'" for i in ids)
            self._table.delete(f"id IN ({id_list})")

    @staticmethod
    def _row_to_dict(r: dict) -> dict:
        try:
            metadata = json.loads(r["metadata"]) if r.get("metadata") else {}
        except Exception:
            metadata = {}
        return {
            "id":       r.get("id", ""),
            "document": r.get("document", ""),
            "metadata": metadata,
            # cosine distance: 0 = idêntico, 1 = ortogonal — ausente em queries sem vetor (get())
            "distance": r.get("_distance"),
        }


def connect(path: str) -> "lancedb.DBConnection":
    return lancedb.connect(path)
