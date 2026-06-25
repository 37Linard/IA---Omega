import subprocess
import sys
import tempfile
import os

DOCKER_IMAGE = "python:3.12-slim"
DOCKER_TIMEOUT = 15  # seconds


def _docker_available() -> bool:
    try:
        r = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except Exception:
        return False


def _run_in_docker(code: str) -> str:
    result = subprocess.run(
        [
            "docker", "run",
            "--rm",                          # auto-remove
            "--network", "none",             # sem rede
            "--memory", "128m",              # limite RAM
            "--cpus", "0.5",                 # limite CPU
            "--read-only",                   # filesystem read-only
            "--tmpfs", "/tmp:size=10m,uid=65534,gid=65534",
            "--user", "nobody",              # não-root
            "--pids-limit", "50",            # previne fork bomb
            "--cap-drop", "ALL",             # sem capabilities Linux
            "--security-opt", "no-new-privileges:true",
            "-i",                            # lê código via stdin
            DOCKER_IMAGE,
            "python", "-"
        ],
        input=code,
        capture_output=True,
        text=True,
        timeout=DOCKER_TIMEOUT
    )

    output = ""
    if result.stdout.strip():
        output += f"STDOUT:\n{result.stdout.strip()}"
    if result.stderr.strip():
        sep = "\n" if output else ""
        output += f"{sep}STDERR:\n{result.stderr.strip()}"
    return output or "Código executado sem saída."


def _run_local_fallback(code: str) -> str:
    """Fallback sem Docker: executa localmente com timeout."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=tempfile.gettempdir()
        )
        output = ""
        if result.stdout.strip():
            output += f"STDOUT:\n{result.stdout.strip()}"
        if result.stderr.strip():
            sep = "\n" if output else ""
            output += f"{sep}STDERR:\n{result.stderr.strip()}"
        return output or "Código executado sem saída."
    except subprocess.TimeoutExpired:
        return "Erro: execução excedeu 10 segundos e foi encerrada."
    except Exception as e:
        return f"Erro ao executar código: {str(e)}"
    finally:
        os.unlink(tmp_path)


class RunPythonTool:
    name = "run_python"
    description = (
        "Escreve e executa código Python em sandbox Docker isolado. "
        "Retorna stdout e stderr. "
        "Input: {'code': 'print(1+1)'}"
    )

    def run(self, input_data: dict) -> str:
        code = input_data.get("code", "")
        if not code.strip():
            return "Erro: campo 'code' obrigatório."

        if _docker_available():
            try:
                return _run_in_docker(code)
            except subprocess.TimeoutExpired:
                return "Erro: execução excedeu 15 segundos e foi encerrada."
            except Exception as e:
                return f"Erro no Docker: {str(e)}"
        else:
            # Docker não disponível — avisa e roda localmente
            result = _run_local_fallback(code)
            return f"[AVISO: Docker não disponível, execução local]\n{result}"
