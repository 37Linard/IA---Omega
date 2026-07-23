import tools.screenshot_tool as ss_mod
from tools.screenshot_tool import ScreenshotTool


def test_saves_screenshot_to_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(ss_mod, "WORKSPACE", str(tmp_path))
    import pyautogui
    captured = {}
    monkeypatch.setattr(pyautogui, "screenshot", lambda path: captured.setdefault("path", path))

    result = ScreenshotTool().run({})

    assert "salvo" in result.lower()
    assert captured["path"].startswith(str(tmp_path))
    assert captured["path"].endswith(".png")


def test_error_handled_cleanly(tmp_path, monkeypatch):
    monkeypatch.setattr(ss_mod, "WORKSPACE", str(tmp_path))
    import pyautogui

    def boom(path):
        raise RuntimeError("sem display")
    monkeypatch.setattr(pyautogui, "screenshot", boom)

    result = ScreenshotTool().run({})

    assert "Erro" in result
