import os


SAFE_DIR = r"C:\Users\User\Desktop\MEU\IA\workspace"


class WriteFileTool:
    name = "write_file"
    description = (
        "Cria ou sobrescreve um arquivo com conteúdo. "
        "Só escreve dentro da pasta workspace segura. "
        "Input: {'filename': 'nome.txt', 'content': 'conteúdo aqui'}"
    )

    def run(self, input_data: dict) -> str:
        filename = input_data.get("filename", "")
        content  = input_data.get("content", "")

        if not filename:
            return "Erro: campo 'filename' obrigatório."

        # Força escrita apenas no workspace seguro
        os.makedirs(SAFE_DIR, exist_ok=True)
        safe_path = os.path.join(SAFE_DIR, os.path.basename(filename))

        try:
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Arquivo criado: {safe_path}"
        except Exception as e:
            return f"Erro ao escrever arquivo: {str(e)}"
