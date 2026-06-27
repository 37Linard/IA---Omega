"""
run_python — executa código Python em sandbox Docker isolado.
Hierarquia: ia-sandbox:latest → python:3.12-slim → execução local (aviso).
"""
import os
import subprocess
import sys
import tempfile
import time

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_DIR   = os.path.join(_PROJECT, "workspace")
SANDBOX_IMAGE   = "ia-sandbox:latest"
FALLBACK_IMAGE  = "python:3.12-slim"
DOCKER_TIMEOUT  = 30   # segundos
MEM_LIMIT       = "256m"
CPU_LIMIT       = "1.0"
PIDS_LIMIT      = "64"
MAX_OUTPUT      = 4000  # chars


# ---------------------------------------------------------------------------
# Detecção
# ---------------------------------------------------------------------------
def _docker_running() -> bool:
    try:
        r = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except Exception:
        return False


def _image_exists(image: str) -> bool:
    try:
        r = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except Exception:
        return False


def get_sandbox_status() -> dict:
    """Usado pelo endpoint /sandbox/status da API."""
    docker_ok = _docker_running()
    if not docker_ok:
        return {"mode": "local", "docker": False, "image": None,
                "warning": "Docker nao disponivel — execucao direta no host"}
    sandbox_ok = _image_exists(SANDBOX_IMAGE)
    image = SANDBOX_IMAGE if sandbox_ok else FALLBACK_IMAGE
    return {
        "mode":   "docker",
        "docker": True,
        "image":  image,
        "custom": sandbox_ok,
        "warning": None if sandbox_ok else f"Imagem {SANDBOX_IMAGE} nao buildada — usando {FALLBACK_IMAGE}. Execute build_sandbox.bat.",
    }


# ---------------------------------------------------------------------------
# Execução Docker
# ---------------------------------------------------------------------------
def _run_in_docker(code: str, image: str) -> tuple[str, int, float]:
    """Retorna (output, exit_code, elapsed_s)."""
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    workspace_abs = os.path.abspath(WORKSPACE_DIR).replace("\\", "/")

    cmd = [
        "docker", "run",
        "--rm",
        "--network", "none",
        "--memory", MEM_LIMIT,
        "--cpus", CPU_LIMIT,
        "--pids-limit", PIDS_LIMIT,
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "--user", "65534:65534",
        "--tmpfs", "/tmp:size=32m",
        "-v", f"{workspace_abs}:/workspace:ro",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "PYTHONUNBUFFERED=1",
        "-i",
        image,
        "python", "-"
    ]

    t0 = time.monotonic()
    result = subprocess.run(
        cmd,
        input=code,
        capture_output=True,
        text=True,
        timeout=DOCKER_TIMEOUT,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = round(time.monotonic() - t0, 2)

    parts = []
    if result.stdout.strip():
        parts.append(f"STDOUT:\n{result.stdout.strip()}")
    if result.stderr.strip():
        parts.append(f"STDERR:\n{result.stderr.strip()}")

    output = "\n".join(parts) if parts else "Codigo executado sem saida."
    if len(output) > MAX_OUTPUT:
        output = output[:MAX_OUTPUT] + "\n[... saida truncada ...]"

    return output, result.returncode, elapsed


# ---------------------------------------------------------------------------
# Fallback local
# ---------------------------------------------------------------------------
def _run_local(code: str) -> tuple[str, int, float]:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    t0 = time.monotonic()
    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=WORKSPACE_DIR,
            encoding="utf-8",
            errors="replace",
        )
        elapsed = round(time.monotonic() - t0, 2)
        parts = []
        if result.stdout.strip():
            parts.append(f"STDOUT:\n{result.stdout.strip()}")
        if result.stderr.strip():
            parts.append(f"STDERR:\n{result.stderr.strip()}")
        output = "\n".join(parts) if parts else "Codigo executado sem saida."
        if len(output) > MAX_OUTPUT:
            output = output[:MAX_OUTPUT] + "\n[... saida truncada ...]"
        return output, result.returncode, elapsed
    except subprocess.TimeoutExpired:
        return "Erro: execucao excedeu 15 segundos.", 1, 15.0
    except Exception as e:
        return f"Erro: {e}", 1, 0.0
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------
class RunPythonTool:
    name = "run_python"
    description = (
        "Executa codigo Python em sandbox Docker isolado (sem rede, memoria limitada). "
        "Pode ler arquivos de /workspace. Retorna stdout/stderr. "
        "Input: {'code': 'print(1+1)'}"
    )

    def run(self, input_data: dict) -> str:
        code = input_data.get("code", "").strip()
        if not code:
            return "Erro: campo 'code' obrigatorio."

        if _docker_running():
            image = SANDBOX_IMAGE if _image_exists(SANDBOX_IMAGE) else FALLBACK_IMAGE
            try:
                output, exit_code, elapsed = _run_in_docker(code, image)
                header = f"[sandbox: {image} | {elapsed}s | exit={exit_code}]"
                return f"{header}\n{output}"
            except subprocess.TimeoutExpired:
                return f"[sandbox: {image}]\nErro: execucao excedeu {DOCKER_TIMEOUT}s."
            except Exception as e:
                output, exit_code, elapsed = _run_local(code)
                return f"[Docker falhou ({e}) — fallback local | {elapsed}s | exit={exit_code}]\n[AVISO: execucao no host sem isolamento]\n{output}"
        else:
            output, exit_code, elapsed = _run_local(code)
            return (
                f"[local: sem Docker | {elapsed}s | exit={exit_code}]\n"
                f"[AVISO: Docker nao disponivel — execucao direta no host, sem isolamento]\n"
                f"{output}"
            )
