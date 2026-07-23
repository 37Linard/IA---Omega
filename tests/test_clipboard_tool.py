from tools.clipboard_tool import ClipboardTool


def test_read_returns_clipboard_content(monkeypatch):
    import pyperclip
    monkeypatch.setattr(pyperclip, "paste", lambda: "texto copiado")

    result = ClipboardTool().run({"action": "read"})

    assert "texto copiado" in result


def test_read_empty_clipboard(monkeypatch):
    import pyperclip
    monkeypatch.setattr(pyperclip, "paste", lambda: "")

    result = ClipboardTool().run({"action": "read"})

    assert "vazio" in result.lower()


def test_write_copies_text(monkeypatch):
    import pyperclip
    captured = {}
    monkeypatch.setattr(pyperclip, "copy", lambda text: captured.setdefault("text", text))

    result = ClipboardTool().run({"action": "write", "text": "novo conteudo"})

    assert captured["text"] == "novo conteudo"
    assert "novo conteudo" in result


def test_write_without_text_errors():
    result = ClipboardTool().run({"action": "write"})
    assert "obrigatório" in result


def test_invalid_action_errors():
    result = ClipboardTool().run({"action": "delete"})
    assert "inválida" in result
