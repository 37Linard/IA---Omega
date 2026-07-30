import os

import tools.write_file_tool as wf_mod
from tools.write_file_tool import WriteFileTool


def _tool(tmp_path, monkeypatch):
    safe_dir = tmp_path / "workspace"
    monkeypatch.setattr(wf_mod, "SAFE_DIR", str(safe_dir))
    monkeypatch.setattr(wf_mod, "SNAPSHOT_DIR", str(safe_dir / ".file_snapshots"))
    return WriteFileTool(), safe_dir


def test_writes_new_file(tmp_path, monkeypatch):
    tool, safe_dir = _tool(tmp_path, monkeypatch)
    result = tool.run({"filename": "a.txt", "content": "v1"})
    assert "criado" in result.lower()
    assert (safe_dir / "a.txt").read_text(encoding="utf-8") == "v1"


def test_missing_filename_errors():
    result = WriteFileTool().run({"content": "x"})
    assert "obrigatório" in result


def test_filename_without_extension_errors():
    result = WriteFileTool().run({"filename": "semextensao", "content": "x"})
    assert "extensão" in result


def test_overwrite_snapshots_previous_content(tmp_path, monkeypatch):
    tool, safe_dir = _tool(tmp_path, monkeypatch)
    tool.run({"filename": "a.txt", "content": "v1"})
    tool.run({"filename": "a.txt", "content": "v2"})

    assert (safe_dir / "a.txt").read_text(encoding="utf-8") == "v2"
    snaps = list((safe_dir / ".file_snapshots").glob("a.txt.*.bak"))
    assert len(snaps) == 1
    assert snaps[0].read_text(encoding="utf-8") == "v1"


def test_first_write_creates_no_snapshot(tmp_path, monkeypatch):
    tool, safe_dir = _tool(tmp_path, monkeypatch)
    tool.run({"filename": "a.txt", "content": "v1"})
    assert not (safe_dir / ".file_snapshots").exists()


def test_restore_without_snapshot_errors(tmp_path, monkeypatch):
    tool, _ = _tool(tmp_path, monkeypatch)
    result = tool.run({"filename": "a.txt", "action": "restore"})
    assert "erro" in result.lower()
    assert "snapshot" in result.lower()


def test_restore_latest_undoes_last_write(tmp_path, monkeypatch):
    tool, safe_dir = _tool(tmp_path, monkeypatch)
    tool.run({"filename": "a.txt", "content": "v1"})
    tool.run({"filename": "a.txt", "content": "v2"})

    result = tool.run({"filename": "a.txt", "action": "restore"})

    assert "restaurado" in result.lower()
    assert (safe_dir / "a.txt").read_text(encoding="utf-8") == "v1"


def test_restore_is_itself_undoable(tmp_path, monkeypatch):
    """Restaurar tambem tira snapshot do que estava lá antes -- nao é via de
    mão única, dá pra "desfazer o desfazer"."""
    tool, safe_dir = _tool(tmp_path, monkeypatch)
    tool.run({"filename": "a.txt", "content": "v1"})
    tool.run({"filename": "a.txt", "content": "v2"})
    tool.run({"filename": "a.txt", "action": "restore"})  # volta pra v1

    result = tool.run({"filename": "a.txt", "action": "restore"})  # desfaz o restore

    assert (safe_dir / "a.txt").read_text(encoding="utf-8") == "v2"
    assert "restaurado" in result.lower()


def test_restore_specific_version(tmp_path, monkeypatch):
    tool, safe_dir = _tool(tmp_path, monkeypatch)
    tool.run({"filename": "a.txt", "content": "v1"})
    tool.run({"filename": "a.txt", "content": "v2"})
    tool.run({"filename": "a.txt", "content": "v3"})

    versions_out = tool.run({"filename": "a.txt", "action": "list_snapshots"})
    first_version = versions_out.split(": ")[1].split(", ")[0]

    result = tool.run({"filename": "a.txt", "action": "restore", "version": first_version})

    assert "restaurado" in result.lower()
    assert (safe_dir / "a.txt").read_text(encoding="utf-8") == "v1"


def test_restore_unknown_version_errors(tmp_path, monkeypatch):
    tool, _ = _tool(tmp_path, monkeypatch)
    tool.run({"filename": "a.txt", "content": "v1"})
    tool.run({"filename": "a.txt", "content": "v2"})

    result = tool.run({"filename": "a.txt", "action": "restore", "version": "20200101T000000"})
    assert "erro" in result.lower()
    assert "não encontrada" in result.lower()


def test_list_snapshots_empty(tmp_path, monkeypatch):
    tool, _ = _tool(tmp_path, monkeypatch)
    result = tool.run({"filename": "a.txt", "action": "list_snapshots"})
    assert "nenhum snapshot" in result.lower()


def test_list_snapshots_ordered_oldest_first(tmp_path, monkeypatch):
    tool, _ = _tool(tmp_path, monkeypatch)
    tool.run({"filename": "a.txt", "content": "v1"})
    tool.run({"filename": "a.txt", "content": "v2"})
    tool.run({"filename": "a.txt", "content": "v3"})

    result = tool.run({"filename": "a.txt", "action": "list_snapshots"})
    versions = result.split(": ")[1].split(", ")
    assert len(versions) == 2
    assert versions == sorted(versions)


def test_snapshots_scoped_per_filename(tmp_path, monkeypatch):
    tool, _ = _tool(tmp_path, monkeypatch)
    tool.run({"filename": "a.txt", "content": "a1"})
    tool.run({"filename": "a.txt", "content": "a2"})
    tool.run({"filename": "b.txt", "content": "b1"})
    tool.run({"filename": "b.txt", "content": "b2"})

    result = tool.run({"filename": "a.txt", "action": "list_snapshots"})
    assert "a.txt" in result
    assert "b.txt" not in result


def test_prunes_snapshots_beyond_max(tmp_path, monkeypatch):
    tool, safe_dir = _tool(tmp_path, monkeypatch)
    monkeypatch.setattr(wf_mod, "MAX_SNAPSHOTS", 3)

    tool.run({"filename": "a.txt", "content": "v0"})
    for i in range(1, 6):
        tool.run({"filename": "a.txt", "content": f"v{i}"})

    snaps = os.listdir(safe_dir / ".file_snapshots")
    assert len(snaps) == 3


def test_filename_path_traversal_stripped_to_basename(tmp_path, monkeypatch):
    tool, safe_dir = _tool(tmp_path, monkeypatch)
    result = tool.run({"filename": "../evil.txt", "content": "x"})
    assert "criado" in result.lower()
    assert (safe_dir / "evil.txt").is_file()
    assert not (tmp_path / "evil.txt").is_file()
