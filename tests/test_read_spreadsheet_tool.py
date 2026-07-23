import csv
import tools.read_spreadsheet_tool as rs_mod
from tools.read_spreadsheet_tool import ReadSpreadsheetTool


def _write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def test_reads_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(rs_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    f = tmp_path / "dados.csv"
    _write_csv(f, [["nome", "idade"], ["ana", "30"], ["bia", "25"]])

    result = ReadSpreadsheetTool().run({"path": str(f)})

    assert "dados.csv" in result
    assert "nome" in result and "ana" in result


def test_blocks_path_outside_allowed_dirs(tmp_path, monkeypatch):
    allowed = tmp_path / "Desktop"
    outside = tmp_path / "Desktop-secret"
    allowed.mkdir()
    outside.mkdir()
    monkeypatch.setattr(rs_mod, "ALLOWED_READ_DIRS", [str(allowed)])
    f = outside / "dados.csv"
    _write_csv(f, [["a"]])

    result = ReadSpreadsheetTool().run({"path": str(f)})

    assert "Bloqueado" in result


def test_missing_path_errors():
    result = ReadSpreadsheetTool().run({})
    assert "obrigatório" in result


def test_nonexistent_file_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(rs_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    result = ReadSpreadsheetTool().run({"path": str(tmp_path / "nao_existe.csv")})
    assert "não encontrado" in result


def test_unsupported_extension_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(rs_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    f = tmp_path / "dados.txt"
    f.write_text("x", encoding="utf-8")

    result = ReadSpreadsheetTool().run({"path": str(f)})

    assert "não suportado" in result


def test_empty_csv_message(tmp_path, monkeypatch):
    monkeypatch.setattr(rs_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    f = tmp_path / "vazio.csv"
    f.write_text("", encoding="utf-8")

    result = ReadSpreadsheetTool().run({"path": str(f)})

    assert "vazia" in result.lower()


def test_rows_param_capped_at_200(tmp_path, monkeypatch):
    monkeypatch.setattr(rs_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    f = tmp_path / "dados.csv"
    _write_csv(f, [["n"]] + [[str(i)] for i in range(300)])

    result = ReadSpreadsheetTool().run({"path": str(f), "rows": 9999})

    # achado real: a nota de truncamento virava célula da tabela e era cortada em
    # 30 chars pelo formatador, saindo ilegível ("...exib"). Corrigido — fica
    # inteira, fora da tabela.
    assert "linhas no total, exibindo 200" in result
