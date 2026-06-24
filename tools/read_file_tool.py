import os


class ReadFileTool:
    name = "read_file"
    description = "Lê o conteúdo de um arquivo local. Input: {'path': 'caminho/do/arquivo.txt'}"

    def run(self, input_data: dict) -> str:
        path = input_data.get("path", "")

        if not path:
            return "Erro: campo 'path' obrigatório."

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
