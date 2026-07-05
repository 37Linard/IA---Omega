"""Migra dados existentes do ChromaDB (armazenamento vetorial da Fase 1) pro
LanceDB. Roda uma vez, manual:

    python migrate_chroma_to_lancedb.py

Lê workspace/chroma_db (collections sessions/facts, com ou sem sufixo
_nomic — dependia de qual embedder tava ativo antes) e workspace/rag_db
(collection pdf_chunks), reembeda todo o texto com o embedder atual
(embeddings.get_embedder()) e grava em workspace/lance_memory_db e
workspace/rag_lance_db.

Reembeda em vez de copiar os vetores antigos direto porque o embedder pode
ter mudado de modelo — copiar vetores de espaços semânticos diferentes pra
mesma tabela corrompe a busca por similaridade.

NÃO apaga os dados antigos — só lê. Apague workspace/chroma_db e
workspace/rag_db manualmente depois de confirmar que a busca no LanceDB
tá boa.
"""
import os


def _read_chroma_collection(client, name: str):
    try:
        coll = client.get_collection(name)
    except Exception:
        return None
    data = coll.get(include=["documents", "metadatas"])
    ids = data.get("ids") or []
    if not ids:
        return None
    return list(zip(ids, data["documents"], data["metadatas"]))


def migrate_memory():
    import chromadb
    import vector_store
    from embeddings import get_embedder

    old_dir = os.path.join("workspace", "chroma_db")
    if not os.path.isdir(old_dir):
        print("  Sem dados antigos de memória (workspace/chroma_db não existe) — nada a migrar.")
        return

    client = chromadb.PersistentClient(path=old_dir)
    embed_fn, dim, kind = get_embedder()
    new_db = vector_store.connect(os.path.join("workspace", "lance_memory_db"))

    for coll_base in ("sessions", "facts"):
        rows = None
        for candidate in (coll_base, f"{coll_base}_nomic"):
            rows = _read_chroma_collection(client, candidate)
            if rows:
                break
        if not rows:
            print(f"  {coll_base}: nada encontrado no Chroma antigo")
            continue

        ids, docs, metas = zip(*rows)
        vectors = embed_fn(list(docs))
        table = vector_store.LanceCollection(new_db, coll_base, dim)
        table.upsert(list(ids), vectors, list(docs), list(metas))
        print(f"  {coll_base}: {len(ids)} itens migrados (embeddings={kind})")


def migrate_rag():
    import chromadb
    import vector_store
    from embeddings import get_embedder

    old_dir = os.path.join("workspace", "rag_db")
    if not os.path.isdir(old_dir):
        print("  Sem dados antigos de RAG (workspace/rag_db não existe) — nada a migrar.")
        return

    client = chromadb.PersistentClient(path=old_dir)
    rows = _read_chroma_collection(client, "pdf_chunks")
    if not rows:
        print("  pdf_chunks: nada encontrado no Chroma antigo")
        return

    embed_fn, dim, kind = get_embedder()
    ids, docs, metas = zip(*rows)
    vectors = embed_fn(list(docs))
    new_db = vector_store.connect(os.path.join("workspace", "rag_lance_db"))
    table = vector_store.LanceCollection(new_db, "pdf_chunks", dim)
    table.upsert(list(ids), vectors, list(docs), list(metas))
    print(f"  pdf_chunks: {len(ids)} chunks migrados (embeddings={kind})")


if __name__ == "__main__":
    print("Migrando memória (sessions/facts)...")
    migrate_memory()
    print("Migrando RAG (pdf_chunks)...")
    migrate_rag()
    print()
    print("Concluído. Dados antigos NÃO foram apagados (workspace/chroma_db, workspace/rag_db) —")
    print("apague manualmente depois de confirmar que a busca no LanceDB tá boa.")
