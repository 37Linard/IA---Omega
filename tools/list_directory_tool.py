import os


class ListDirectoryTool:
    name = "list_directory"
    description = (
        "Lista arquivos e pastas de um diretório. "
        "Input: {'path': 'C:/caminho/da/pasta'}"
    )

    def run(self, input_data: dict) -> str:
        path = input_data.get("path", "")

        if not path:
            return "Erro: campo 'path' obrigatório."

        if not os.path.exists(path):
            return f"Erro: caminho não encontrado: '{path}'"

        if not os.path.isdir(path):
            return f"Erro: '{path}' não é uma pasta."

        try:
            items = os.listdir(path)
            if not items:
                return "Pasta vazia."

            output = []
            for item in sorted(items):
                full = os.path.join(path, item)
                kind = "DIR " if os.path.isdir(full) else "FILE"
                size = ""
                if os.path.isfile(full):
                    size = f" ({os.path.getsize(full)} bytes)"
                output.append(f"[{kind}] {item}{size}")

            return "\n".join(output)

        except PermissionError:
            return f"Erro: sem permissão para listar '{path}'."
        except Exception as e:
            return f"Erro: {str(e)}"
