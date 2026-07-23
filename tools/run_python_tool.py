"""
run_python — executa código Python isolado.
Hierarquia: WASM (wasmtime, boot quase instantâneo) → Docker (ia-sandbox
→ python:3.12-slim) → execução local (aviso).
"""
import os
import subprocess
import sys
import tempfile
import threading
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

WASM_BINARY        = os.path.join(_PROJECT, "sandbox_wasm", "python-3.12.0.wasm")
WASM_TIMEOUT       = 15                    # segundos
WASM_MEM_LIMIT     = 256 * 1024 * 1024     # bytes — mesmo teto do Docker


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


def _wasm_available() -> bool:
    try:
        import wasmtime  # noqa: F401
    except ImportError:
        return False
    return os.path.isfile(WASM_BINARY)


def get_sandbox_status() -> dict:
    """Usado pelo endpoint /sandbox/status da API."""
    if _wasm_available():
        return {"mode": "wasm", "docker": _docker_running(), "image": "python-3.12.0.wasm",
                "custom": True, "warning": None}

    docker_ok = _docker_running()
    if not docker_ok:
        return {"mode": "local", "docker": False, "image": None,
                "warning": "Nem WASM (rode download_wasm_sandbox.bat) nem Docker disponiveis — execucao direta no host"}
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
# Execução WASM — CPython compilado pra WASI, via wasmtime
# ---------------------------------------------------------------------------
_wasm_engine = None
_wasm_module = None
_wasm_lock   = threading.Lock()


def _get_wasm_module():
    """Compila o módulo WASM uma única vez (custa ~1-2s) e cacheia em memória —
    chamadas seguintes reusam o módulo compilado e só pagam o custo de
    instanciar (poucos ms). É isso que dá o boot quase instantâneo comparado
    ao Docker, que repaga o startup do container a cada `docker run`."""
    global _wasm_engine, _wasm_module
    if _wasm_module is not None:
        return _wasm_engine, _wasm_module
    with _wasm_lock:
        if _wasm_module is None:
            from wasmtime import Config, Engine, Module
            cfg = Config()
            cfg.epoch_interruption = True
            _wasm_engine = Engine(cfg)
            _wasm_module = Module.from_file(_wasm_engine, WASM_BINARY)
    return _wasm_engine, _wasm_module


def _read_and_unlink(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def _run_in_wasm(code: str, timeout_s: int = WASM_TIMEOUT) -> tuple[str, int, float]:
    """Executa via CPython/WASI (wasmtime). Isolamento: sem rede (WASI não
    expõe sockets por padrão), /workspace montado read-only, memória
    limitada, timeout via epoch interruption — interrompe de dentro do
    runtime, sem depender de matar processo externo (o que o Docker faz)."""
    from wasmtime import DirPerms, ExitTrap, FilePerms, Linker, Store, Trap, TrapCode, WasiConfig

    engine, module = _get_wasm_module()
    store = Store(engine)
    store.set_epoch_deadline(1)
    store.set_limits(memory_size=WASM_MEM_LIMIT)

    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    out_f = tempfile.NamedTemporaryFile(delete=False, suffix=".out")
    err_f = tempfile.NamedTemporaryFile(delete=False, suffix=".err")
    out_f.close()
    err_f.close()

    wasi = WasiConfig()
    wasi.argv = ["python", "-c", code]
    wasi.stdout_file = out_f.name
    wasi.stderr_file = err_f.name
    wasi.preopen_dir(os.path.abspath(WORKSPACE_DIR), "/workspace", DirPerms.READ_ONLY, FilePerms.READ_ONLY)
    store.set_wasi(wasi)

    linker = Linker(engine)
    linker.define_wasi()

    t0 = time.monotonic()
    stop_ticking = threading.Event()

    def ticker():
        # single-shot: só incrementa o epoch (global, compartilhado entre chamadas)
        # se a execução NAO terminou dentro do timeout — stop_ticking.set() no
        # finally abaixo cancela isso pro caso comum (execução rápida normal).
        # Incrementar sempre (mesmo em execução normal) vazaria pra próxima
        # chamada, já que o epoch do Engine é compartilhado — foi um bug real
        # detectado testando (2ª chamada dava timeout falso por causa disso).
        if not stop_ticking.wait(timeout_s):
            try:
                engine.increment_epoch()
            except Exception:
                pass

    threading.Thread(target=ticker, daemon=True).start()

    exit_code = 0
    timed_out = False
    try:
        instance = linker.instantiate(store, module)
        start = instance.exports(store)["_start"]
        start(store)
    except ExitTrap as e:
        exit_code = e.code
    except Trap as e:
        timed_out = e.trap_code == TrapCode.INTERRUPT
        exit_code = 1
    except Exception:
        exit_code = 1
    finally:
        stop_ticking.set()

    elapsed = round(time.monotonic() - t0, 2)
    stdout = _read_and_unlink(out_f.name)
    stderr = _read_and_unlink(err_f.name)

    if timed_out:
        return f"Erro: execucao excedeu {timeout_s}s.", 1, elapsed

    parts = []
    if stdout.strip():
        parts.append(f"STDOUT:\n{stdout.strip()}")
    if stderr.strip():
        parts.append(f"STDERR:\n{stderr.strip()}")
    output = "\n".join(parts) if parts else "Codigo executado sem saida."
    if len(output) > MAX_OUTPUT:
        output = output[:MAX_OUTPUT] + "\n[... saida truncada ...]"
    return output, exit_code, elapsed


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
        "Executa codigo Python em sandbox isolado (sem rede, memoria limitada). "
        "Pode ler arquivos de /workspace. Retorna stdout/stderr. "
        "Input: {'code': 'print(1+1)'}"
    )

    def run(self, input_data: dict) -> str:
        code = input_data.get("code", "").strip()
        if not code:
            return "Erro: campo 'code' obrigatorio."

        if _wasm_available():
            try:
                output, exit_code, elapsed = _run_in_wasm(code)
                # WASM só tem stdlib (CPython/WASI puro, sem numpy/pandas/etc) — código
                # que precisa de lib terceira "sucede" tecnicamente (exit_code!=0 normal,
                # não é falha de sandbox) mas nunca chegava no Docker, que tem as libs.
                # Achado 2026-07-23: imagem Docker era efetivamente inalcançável.
                if exit_code != 0 and "ModuleNotFoundError" in output and _docker_running():
                    image = SANDBOX_IMAGE if _image_exists(SANDBOX_IMAGE) else FALLBACK_IMAGE
                    try:
                        d_output, d_exit, d_elapsed = _run_in_docker(code, image)
                        header = f"[sandbox: {image} (retry pos-WASM sem lib) | {d_elapsed}s | exit={d_exit}]"
                        return f"{header}\n{d_output}"
                    except Exception:
                        pass  # Docker tambem falhou — cai pro resultado original do WASM
                header = f"[sandbox: wasm | {elapsed}s | exit={exit_code}]"
                return f"{header}\n{output}"
            except Exception as e:
                # WASM falhou de forma inesperada — cai pra Docker/local em vez de propagar erro
                pass

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
