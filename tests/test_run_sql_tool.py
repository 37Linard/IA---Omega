import tools.run_sql_tool as sql_mod
from tools.run_sql_tool import RunSqlTool


def test_create_insert_select_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(sql_mod, "SAFE_DIR", str(tmp_path))
    tool = RunSqlTool()

    tool.run({"db": "t.db", "query": "CREATE TABLE t (id INTEGER, nome TEXT)"})
    tool.run({"db": "t.db", "query": "INSERT INTO t VALUES (1, 'a')"})
    result = tool.run({"db": "t.db", "query": "SELECT * FROM t"})

    assert "id | nome" in result
    assert "1 | a" in result


def test_missing_db_field_errors():
    result = RunSqlTool().run({"query": "SELECT 1"})
    assert "obrigatório" in result


def test_missing_query_field_errors():
    result = RunSqlTool().run({"db": "t.db"})
    assert "obrigatório" in result


def test_drop_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr(sql_mod, "SAFE_DIR", str(tmp_path))
    result = RunSqlTool().run({"db": "t.db", "query": "DROP TABLE t"})
    assert "Bloqueado" in result


def test_drop_with_newline_instead_of_space_still_blocked(tmp_path, monkeypatch):
    # achado real: bloqueio antigo exigia "DROP " (espaço literal) — "DROP\nTABLE"
    # bypassava porque SQLite trata \n como separador válido também.
    monkeypatch.setattr(sql_mod, "SAFE_DIR", str(tmp_path))
    result = RunSqlTool().run({"db": "t.db", "query": "DROP\nTABLE t"})
    assert "Bloqueado" in result


def test_drop_with_tab_still_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr(sql_mod, "SAFE_DIR", str(tmp_path))
    result = RunSqlTool().run({"db": "t.db", "query": "DROP\tTABLE t"})
    assert "Bloqueado" in result


def test_select_on_empty_result(tmp_path, monkeypatch):
    monkeypatch.setattr(sql_mod, "SAFE_DIR", str(tmp_path))
    tool = RunSqlTool()
    tool.run({"db": "t.db", "query": "CREATE TABLE t (id INTEGER)"})

    result = tool.run({"db": "t.db", "query": "SELECT * FROM t"})

    assert "0 resultados" in result


def test_invalid_sql_returns_clean_error(tmp_path, monkeypatch):
    monkeypatch.setattr(sql_mod, "SAFE_DIR", str(tmp_path))
    result = RunSqlTool().run({"db": "t.db", "query": "SELECT * FROM tabela_inexistente"})
    assert "Erro SQL" in result


def test_db_name_confined_to_safe_dir_via_basename(tmp_path, monkeypatch):
    monkeypatch.setattr(sql_mod, "SAFE_DIR", str(tmp_path))
    RunSqlTool().run({"db": "../../evil.db", "query": "CREATE TABLE t (id INTEGER)"})

    # basename() reduz "../../evil.db" pra "evil.db", confinado no SAFE_DIR
    assert (tmp_path / "evil.db").exists()
    assert not (tmp_path.parent.parent / "evil.db").exists()
