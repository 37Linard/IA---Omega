import tools.read_file_tool as rf_mod
from tools.read_file_tool import ReadFileTool


def test_reads_allowed_file(tmp_path, monkeypatch):
    monkeypatch.setattr(rf_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    f = tmp_path / "nota.txt"
    f.write_text("conteudo real", encoding="utf-8")

    result = ReadFileTool().run({"path": str(f)})

    assert result == "conteudo real"


def test_blocks_path_outside_allowed_dirs(tmp_path, monkeypatch):
    allowed = tmp_path / "Desktop"
    outside = tmp_path / "Desktop-secret"
    allowed.mkdir()
    outside.mkdir()
    monkeypatch.setattr(rf_mod, "ALLOWED_READ_DIRS", [str(allowed)])
    f = outside / "segredo.txt"
    f.write_text("nao deveria ler", encoding="utf-8")

    result = ReadFileTool().run({"path": str(f)})

    assert "Bloqueado" in result


def test_missing_path_field_errors():
    result = ReadFileTool().run({})
    assert "obrigatório" in result


def test_nonexistent_file_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(rf_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])

    result = ReadFileTool().run({"path": str(tmp_path / "nao_existe.txt")})

    assert "não encontrado" in result


def test_empty_file_message(tmp_path, monkeypatch):
    monkeypatch.setattr(rf_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    f = tmp_path / "vazio.txt"
    f.write_text("   ", encoding="utf-8")

    result = ReadFileTool().run({"path": str(f)})

    assert "vazio" in result.lower()


def test_large_file_truncated(tmp_path, monkeypatch):
    monkeypatch.setattr(rf_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    f = tmp_path / "grande.txt"
    f.write_text("x" * 5000, encoding="utf-8")

    result = ReadFileTool().run({"path": str(f)})

    assert "truncado" in result
    assert len(result) < 5000
