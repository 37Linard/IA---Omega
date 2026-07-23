import os
from config import ALLOWED_READ_DIRS
from tools._paths import is_allowed_path


def _is_allowed(path: str) -> bool:
    return is_allowed_path(path, ALLOWED_READ_DIRS)


class ReadFileTool:
    name = "read_file"
    description = "Lê o conteúdo de um arquivo local. Input: {'path': 'caminho/do/arquivo.txt'}"

    def run(self, input_data: dict) -> str:
        path = input_data.get("path", "")

        if not path:
            return "Erro: campo 'path' obrigatório."

        if not _is_allowed(path):
            return f"Bloqueado: '{path}' fora das pastas permitidas (Desktop, Documents, Downloads, workspace)."

        if not os.path.exists(path):
            return f"Erro: arquivo não encontrado em '{path}'."

        if not os.path.isfile(path):
            return f"Erro: '{path}' não é um arquivo."

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                return "Arquivo existe mas está vazio."

            # limita a 3000 chars pra não explodir contexto do LLM
            if len(content) > 3000:
                return content[:3000] + "\n\n[... arquivo truncado — muito longo ...]"

            return content

        except PermissionError:
            return f"Erro: sem permissão para ler '{path}'."
        except Exception as e:
            return f"Erro inesperado: {str(e)}"
