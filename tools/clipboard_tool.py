class ClipboardTool:
    name = "clipboard"
    description = (
        "Lê ou escreve na área de transferência do Windows. "
        "Input: {'action': 'read'} ou {'action': 'write', 'text': 'conteúdo'}"
    )

    def run(self, input_data: dict) -> str:
        try:
            import pyperclip
        except ImportError:
            return "Erro: instale pyperclip — pip install pyperclip"

        action = input_data.get("action", "read")
        try:
            if action == "read":
                text = pyperclip.paste()
                return f"Clipboard: {text[:1000]}" if text else "Clipboard vazio."
            elif action == "write":
                text = input_data.get("text", "")
                if not text:
                    return "Erro: campo 'text' obrigatório."
                pyperclip.copy(text)
                return f"Copiado para clipboard: {text[:100]}"
            else:
                return f"Ação '{action}' inválida. Use 'read' ou 'write'."
        except Exception as e:
            return f"Erro: {str(e)}"
