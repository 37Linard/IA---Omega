import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rag import get_rag_index
from memory import Memory
from tools._security import wrap_untrusted


class RagSearchTool:
    name        = "rag_search"
    description = (
        "Busca semântica em PDFs indexados e em resumos de sessões de conversa anteriores (memória episódica). "
        "Use quando a tarefa mencionar documentos, PDFs, contratos, relatórios, arquivos enviados, "
        "ou perguntar sobre o que foi feito/pedido em conversas passadas. "
        'Input: {"query": "o que diz o contrato sobre rescisão", "n": 5} '
        'ou {"query": "...", "file": "nome_do_arquivo.pdf"} para filtrar por arquivo (desativa busca em sessões).'
    )

    def __init__(self):
        self.memory = None  # injetado lazy no primeiro run() — evita custo de LanceDB no import

    def run(self, params: dict) -> str:
        query       = params.get("query", "").strip()
        n           = int(params.get("n", 5))
        file_filter = params.get("file") or None

        if not query:
            return "Erro: forneça 'query' para buscar nos documentos."

        if self.memory is None:
            self.memory = Memory()

        index       = get_rag_index()
        doc_results = index.search(query, n=n, file_filter=file_filter) if index.list_docs() else []
        episodes    = [] if file_filter else self.memory.search_episodes(query, n=3)

        if not doc_results and not episodes:
            return "Nenhum trecho relevante encontrado, nem em documentos nem em sessões anteriores."

        lines = [f"Trechos mais relevantes para: '{query}'\n"]
        for i, r in enumerate(doc_results, 1):
            lines.append(
                f"[{i}] {r['file']} — pág. {r['page']} (score: {r['score']})\n"
                f"{r['text'][:400]}\n"
            )
        for i, e in enumerate(episodes, 1):
            ts = (e.get("ts") or e.get("timestamp") or "")[:10]
            lines.append(f"[sessão anterior {i}] {ts}\n{e.get('summary', '')}\n")

        return wrap_untrusted(f"documentos indexados + sessões anteriores: {query}", "\n".join(lines))
