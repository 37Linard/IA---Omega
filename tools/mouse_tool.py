class MouseTool:
    name = "mouse"
    description = (
        "Move ou clica o mouse em coordenadas da tela. "
        "Input: {'action': 'click', 'x': 100, 'y': 200} "
        "ou {'action': 'move', 'x': 100, 'y': 200} "
        "ou {'action': 'position'} para ver posição atual"
    )

    def run(self, input_data: dict) -> str:
        try:
            import pyautogui
        except ImportError:
            return "Erro: instale pyautogui — pip install pyautogui"

        action = input_data.get("action", "position")
        try:
            if action == "position":
                x, y = pyautogui.position()
                return f"Posição atual do mouse: ({x}, {y})"
            elif action in ("click", "move"):
                x = int(input_data.get("x", 0))
                y = int(input_data.get("y", 0))
                pyautogui.moveTo(x, y, duration=0.3)
                if action == "click":
                    pyautogui.click()
                    return f"Clicou em ({x}, {y})"
                return f"Mouse movido para ({x}, {y})"
            else:
                return f"Ação '{action}' inválida. Use 'click', 'move' ou 'position'."
        except Exception as e:
            return f"Erro: {str(e)}"
