class KeyboardTool:
    name = "keyboard"
    description = (
        "Digita texto ou pressiona teclas no computador. "
        "Input: {'action': 'type', 'text': 'hello'} "
        "ou {'action': 'press', 'key': 'ctrl+c'}"
    )

    def run(self, input_data: dict) -> str:
        try:
            import pyautogui
        except ImportError:
            return "Erro: instale pyautogui — pip install pyautogui"

        action = input_data.get("action", "type")
        try:
            if action == "type":
                text = input_data.get("text", "")
                pyautogui.typewrite(text, interval=0.05)
                return f"Digitado: {text[:80]}"
            elif action == "press":
                key  = input_data.get("key", "")
                keys = [k.strip() for k in key.split("+")]
                if len(keys) > 1:
                    pyautogui.hotkey(*keys)
                else:
                    pyautogui.press(keys[0])
                return f"Tecla: {key}"
            else:
                return f"Ação '{action}' inválida. Use 'type' ou 'press'."
        except Exception as e:
            return f"Erro: {str(e)}"
