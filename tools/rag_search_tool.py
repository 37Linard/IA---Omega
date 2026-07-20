import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rag import get_rag_index
from tools._security import wrap_untrusted


class RagSearchTool:
    name        = "rag_search"
    description = (
        "Busca semântica em PDFs indexados. "
        "Use quando a tarefa mencionar documentos, PDFs, contratos, relatórios ou arquivos enviados. "
        'Input: {"query": "o que diz o contrato sobre rescisão", "n": 5} '
        'ou {"query": "...", "file": "nome_do_arquivo.pdf"} para filtrar por arquivo.'
    )

    def run(self, params: dict) -> str:
        query       = params.get("query", "").strip()
        n           = int(params.get("n", 5))
        file_filter = params.get("file") or None

        if not query:
            return "Erro: forneça 'query' para buscar nos documentos."

        index   = get_rag_index()
        docs    = index.list_docs()

        if not docs:
            return "Nenhum PDF indexado ainda. Envie um PDF pelo botão de upload e ele será indexado automaticamente."

        results = index.search(query, n=n, file_filter=file_filter)

        if not results:
            return "Nenhum trecho relevante encontrado para a consulta."

        lines = [f"Trechos mais relevantes para: '{query}'\n"]
        for i, r in enumerate(results, 1):
            lines.append(
                f"[{i}] {r['file']} — pág. {r['page']} (score: {r['score']})\n"
                f"{r['text'][:400]}\n"
            )
        return wrap_untrusted(f"documentos indexados: {query}", "\n".join(lines))
