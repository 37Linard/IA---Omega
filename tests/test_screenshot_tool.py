import sys
import types

import tools.screenshot_tool as ss_mod
from tools.screenshot_tool import ScreenshotTool


def _install_fake_pyautogui(monkeypatch, screenshot_fn):
    # pyautogui real tenta conectar num X server (Xlib) já na importação em
    # Linux — em CI headless isso quebra antes mesmo de eu poder mockar
    # .screenshot. Substitui o módulo inteiro em sys.modules antes do "import
    # pyautogui" (lazy, dentro de run()) rodar — real nunca é tocado. Achado
    # 2026-07-23, CI (ubuntu-latest, sem X11).
    fake = types.ModuleType("pyautogui")
    fake.screenshot = screenshot_fn
    monkeypatch.setitem(sys.modules, "pyautogui", fake)


def test_saves_screenshot_to_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(ss_mod, "WORKSPACE", str(tmp_path))
    captured = {}
    _install_fake_pyautogui(monkeypatch, lambda path: captured.setdefault("path", path))

    result = ScreenshotTool().run({})

    assert "salvo" in result.lower()
    assert captured["path"].startswith(str(tmp_path))
    assert captured["path"].endswith(".png")


def test_error_handled_cleanly(tmp_path, monkeypatch):
    monkeypatch.setattr(ss_mod, "WORKSPACE", str(tmp_path))

    def boom(path):
        raise RuntimeError("sem display")
    _install_fake_pyautogui(monkeypatch, boom)

    result = ScreenshotTool().run({})

    assert "Erro" in result
