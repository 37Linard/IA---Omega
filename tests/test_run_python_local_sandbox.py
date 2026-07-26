import tools.run_python_tool as rpt
from tools.run_python_tool import RunPythonTool


def _force_local_path(monkeypatch):
    monkeypatch.setattr(rpt, "_wasm_available", lambda: False)
    monkeypatch.setattr(rpt, "_docker_running", lambda: False)


def test_local_fallback_uses_job_object_when_available(monkeypatch):
    _force_local_path(monkeypatch)
    monkeypatch.setattr(rpt._winsandbox, "available", lambda: True)
    monkeypatch.setattr(
        rpt._winsandbox, "run_capped",
        lambda cmd, cwd, timeout_s, mem_limit_bytes, **kw: (0, "2\n", "", False),
    )

    result = RunPythonTool().run({"code": "print(1+1)"})

    assert "Job Object" in result
    assert "STDOUT:\n2" in result
    assert "sem isolamento de rede/filesystem" in result  # aviso reduzido, nao mais "sem isolamento" total


def test_local_fallback_without_job_object_warns_no_isolation(monkeypatch):
    _force_local_path(monkeypatch)
    monkeypatch.setattr(rpt._winsandbox, "available", lambda: False)

    result = RunPythonTool().run({"code": "print(1+1)"})

    assert "sem isolamento" in result
    assert "STDOUT:\n2" in result


def test_local_fallback_job_object_setup_fails_degrades_to_plain_subprocess(monkeypatch):
    _force_local_path(monkeypatch)
    monkeypatch.setattr(rpt._winsandbox, "available", lambda: True)

    def boom(*a, **kw):
        raise OSError("CreateJobObjectW falhou")
    monkeypatch.setattr(rpt._winsandbox, "run_capped", boom)

    result = RunPythonTool().run({"code": "print(1+1)"})

    assert "sem isolamento" in result
    assert "STDOUT:\n2" in result


def test_local_fallback_timeout_reports_error(monkeypatch):
    _force_local_path(monkeypatch)
    monkeypatch.setattr(rpt._winsandbox, "available", lambda: True)
    monkeypatch.setattr(
        rpt._winsandbox, "run_capped",
        lambda cmd, cwd, timeout_s, mem_limit_bytes, **kw: (1, "", "", True),
    )

    result = RunPythonTool().run({"code": "while True: pass"})

    assert "excedeu 15 segundos" in result
