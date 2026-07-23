import tools.list_directory_tool as ld_mod
from tools.list_directory_tool import ListDirectoryTool


def test_lists_files_and_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(ld_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    (tmp_path / "arquivo.txt").write_text("x", encoding="utf-8")
    (tmp_path / "subpasta").mkdir()

    result = ListDirectoryTool().run({"path": str(tmp_path)})

    assert "[FILE] arquivo.txt" in result
    assert "[DIR ] subpasta" in result


def test_blocks_path_outside_allowed_dirs(tmp_path, monkeypatch):
    allowed = tmp_path / "Desktop"
    outside = tmp_path / "Desktop-secret"
    allowed.mkdir()
    outside.mkdir()
    monkeypatch.setattr(ld_mod, "ALLOWED_READ_DIRS", [str(allowed)])

    result = ListDirectoryTool().run({"path": str(outside)})

    assert "Bloqueado" in result


def test_empty_dir_message(tmp_path, monkeypatch):
    monkeypatch.setattr(ld_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    empty = tmp_path / "vazia"
    empty.mkdir()

    result = ListDirectoryTool().run({"path": str(empty)})

    assert result == "Pasta vazia."


def test_nonexistent_path_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(ld_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])

    result = ListDirectoryTool().run({"path": str(tmp_path / "nao_existe")})

    assert "não encontrado" in result


def test_path_that_is_a_file_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(ld_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    f = tmp_path / "arquivo.txt"
    f.write_text("x", encoding="utf-8")

    result = ListDirectoryTool().run({"path": str(f)})

    assert "não é uma pasta" in result
