import tools.save_note_tool as sn_mod
from tools.save_note_tool import SaveNoteTool


def test_saves_note_with_frontmatter(tmp_path, monkeypatch):
    monkeypatch.setattr(sn_mod, "OBSIDIAN_DIR", str(tmp_path))
    monkeypatch.setattr(sn_mod, "link_note_in_conversas_index", lambda *a, **kw: None)

    result = SaveNoteTool().run({"title": "Minha Nota", "content": "conteudo aqui"})

    assert "salva" in result.lower()
    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert "tags: [agente-ia]" in text
    assert "# Minha Nota" in text
    assert "conteudo aqui" in text


def test_missing_title_errors():
    result = SaveNoteTool().run({"content": "x"})
    assert "obrigatório" in result


def test_missing_content_errors():
    result = SaveNoteTool().run({"title": "x"})
    assert "obrigatório" in result


def test_illegal_filename_chars_stripped(tmp_path, monkeypatch):
    monkeypatch.setattr(sn_mod, "OBSIDIAN_DIR", str(tmp_path))
    monkeypatch.setattr(sn_mod, "link_note_in_conversas_index", lambda *a, **kw: None)

    SaveNoteTool().run({"title": 'Nota: com <chars> "ilegais"/ | ?*', "content": "x"})

    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    for bad in '<>:"/\\|?*':
        assert bad not in files[0].name


def test_calls_link_note_in_conversas_index(tmp_path, monkeypatch):
    monkeypatch.setattr(sn_mod, "OBSIDIAN_DIR", str(tmp_path))
    calls = []
    monkeypatch.setattr(sn_mod, "link_note_in_conversas_index", lambda d, f: calls.append((d, f)))

    SaveNoteTool().run({"title": "Nota", "content": "x"})

    assert len(calls) == 1
    assert calls[0][0] == str(tmp_path)
