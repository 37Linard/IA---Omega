import os
from datetime import datetime

WORKSPACE = r"C:\Users\User\Desktop\MEU\IA\workspace"


class ScreenshotTool:
    name = "screenshot"
    description = (
        "Tira screenshot da tela atual e salva no workspace. "
        "Input: {} (sem parâmetros)"
    )

    def run(self, input_data: dict) -> str:
        try:
            import pyautogui
            ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{ts}.png"
            filepath = os.path.join(WORKSPACE, filename)
            os.makedirs(WORKSPACE, exist_ok=True)
            pyautogui.screenshot(filepath)
            return f"Screenshot salvo: {filepath}"
        except ImportError:
            return "Erro: instale pyautogui — pip install pyautogui Pillow"
        except Exception as e:
            return f"Erro: {str(e)}"
