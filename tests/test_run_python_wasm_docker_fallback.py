import tools.run_python_tool as rpt
from tools.run_python_tool import RunPythonTool


def test_module_not_found_in_wasm_retries_in_docker(monkeypatch):
    # achado real 2026-07-23: WASM só tem stdlib — código com numpy "sucedia"
    # tecnicamente (exit_code!=0 sem exceção) e nunca chegava no Docker, que tem
    # numpy/pandas/etc. Imagem Docker ficava efetivamente inalcançável.
    monkeypatch.setattr(rpt, "_wasm_available", lambda: True)
    monkeypatch.setattr(rpt, "_run_in_wasm", lambda code: (
        "STDERR:\nModuleNotFoundError: No module named 'numpy'", 1, 0.05
    ))
    monkeypatch.setattr(rpt, "_docker_running", lambda: True)
    monkeypatch.setattr(rpt, "_image_exists", lambda image: True)
    monkeypatch.setattr(rpt, "_run_in_docker", lambda code, image: ("STDOUT:\n6", 0, 0.8))

    result = RunPythonTool().run({"code": "import numpy; print(numpy.array([1,2,3]).sum())"})

    assert "sandbox: ia-sandbox:latest" in result
    assert "STDOUT:\n6" in result


def test_normal_wasm_success_does_not_touch_docker(monkeypatch):
    monkeypatch.setattr(rpt, "_wasm_available", lambda: True)
    monkeypatch.setattr(rpt, "_run_in_wasm", lambda code: ("STDOUT:\n2", 0, 0.05))

    def boom(*a, **kw):
        raise AssertionError("Docker nao deveria ser chamado quando WASM ja teve sucesso")
    monkeypatch.setattr(rpt, "_docker_running", boom)
    monkeypatch.setattr(rpt, "_run_in_docker", boom)

    result = RunPythonTool().run({"code": "print(1+1)"})

    assert "sandbox: wasm" in result
    assert "STDOUT:\n2" in result


def test_real_code_error_in_wasm_does_not_retry_in_docker(monkeypatch):
    # erro de verdade do usuário (não ausência de lib) não deve mascarar/reexecutar
    monkeypatch.setattr(rpt, "_wasm_available", lambda: True)
    monkeypatch.setattr(rpt, "_run_in_wasm", lambda code: (
        "STDERR:\nZeroDivisionError: division by zero", 1, 0.05
    ))

    def boom(*a, **kw):
        raise AssertionError("Docker nao deveria ser chamado pra erro real do usuario")
    monkeypatch.setattr(rpt, "_docker_running", boom)
    monkeypatch.setattr(rpt, "_run_in_docker", boom)

    result = RunPythonTool().run({"code": "1/0"})

    assert "sandbox: wasm" in result
    assert "ZeroDivisionError" in result


def test_module_not_found_but_docker_not_running_falls_back_to_wasm_result(monkeypatch):
    monkeypatch.setattr(rpt, "_wasm_available", lambda: True)
    monkeypatch.setattr(rpt, "_run_in_wasm", lambda code: (
        "STDERR:\nModuleNotFoundError: No module named 'numpy'", 1, 0.05
    ))
    monkeypatch.setattr(rpt, "_docker_running", lambda: False)

    result = RunPythonTool().run({"code": "import numpy"})

    assert "sandbox: wasm" in result
    assert "ModuleNotFoundError" in result
