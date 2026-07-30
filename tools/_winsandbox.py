"""Job Object do Windows — teto real de memoria/processos pro fallback local
do run_python (sem sufixo _tool.py de proposito, tool_loader ignora, igual
_security.py/_paths.py/_schema.py).

Nao e isolamento completo (sem rede/filesystem namespace, ao contrario do
Docker/WASM) -- e o que da pra fazer sem admin e sem dependencia nova (so
ctypes/stdlib). Cobre os dois buracos reais do fallback anterior:
1. Sem teto de memoria nenhum -- um `while True: x=[]; x.append(...)` podia
   estourar a RAM do host inteiro. Job Object com JOB_OBJECT_LIMIT_PROCESS_MEMORY
   faz a alocacao falhar dentro do processo (MemoryError em vez de OOM do host).
2. `subprocess.run(timeout=...)` so mata o filho direto -- codigo malicioso que
   faz fork/spawn (ex: multiprocessing) sobrevive ao timeout. JOB_OBJECT_LIMIT_
   KILL_ON_JOB_CLOSE mata a arvore inteira ao fechar o handle do job.
"""
import ctypes
import subprocess

_kernel32 = ctypes.windll.kernel32 if hasattr(ctypes, "windll") else None

JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JobObjectExtendedLimitInformation = 9
PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [(n, ctypes.c_uint64) for n in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_void_p),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def available() -> bool:
    return _kernel32 is not None


def _make_job(mem_limit_bytes: int, active_process_limit: int):
    assert _kernel32 is not None  # só chamado depois de available() checar
    hjob = _kernel32.CreateJobObjectW(None, None)
    if not hjob:
        raise OSError("CreateJobObjectW falhou")
    info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = (
        JOB_OBJECT_LIMIT_PROCESS_MEMORY
        | JOB_OBJECT_LIMIT_ACTIVE_PROCESS
        | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    )
    info.BasicLimitInformation.ActiveProcessLimit = active_process_limit
    info.ProcessMemoryLimit = mem_limit_bytes
    ok = _kernel32.SetInformationJobObject(
        hjob, JobObjectExtendedLimitInformation,
        ctypes.byref(info), ctypes.sizeof(info),
    )
    if not ok:
        _kernel32.CloseHandle(hjob)
        raise OSError("SetInformationJobObject falhou")
    return hjob


def run_capped(cmd, cwd, timeout_s, mem_limit_bytes, active_process_limit=8, **popen_kwargs):
    """Roda cmd dentro de um Job Object com teto de memoria + limite de
    processos ativos (protecao fork-bomb) + kill-on-job-close (mata a arvore
    inteira em timeout, nao so o filho direto). Retorna
    (returncode, stdout, stderr, timed_out). Levanta OSError se a API do Job
    Object falhar -- quem chama deve ter fallback (subprocess.run puro)."""
    if not available():
        raise OSError("Job Object API indisponivel (nao-Windows)")
    assert _kernel32 is not None  # garantido por available()

    hjob = _make_job(mem_limit_bytes, active_process_limit)
    hprocess = None
    proc = subprocess.Popen(cmd, cwd=cwd, **popen_kwargs)
    try:
        hprocess = _kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, proc.pid)
        if not hprocess or not _kernel32.AssignProcessToJobObject(hjob, hprocess):
            proc.kill()
            proc.wait()
            raise OSError("AssignProcessToJobObject falhou")
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
            return proc.returncode, stdout, stderr, False
        except subprocess.TimeoutExpired:
            _kernel32.TerminateJobObject(hjob, 1)
            stdout, stderr = proc.communicate()
            return proc.returncode, stdout, stderr, True
    finally:
        if hprocess:
            _kernel32.CloseHandle(hprocess)
        _kernel32.CloseHandle(hjob)
