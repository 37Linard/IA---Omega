import ctypes
import subprocess

import tools._winsandbox as ws


class _FakeProc:
    def __init__(self, comm_results, pid=4242):
        self.pid = pid
        self._comm_results = list(comm_results)
        self.killed = False
        self.waited = False
        self.returncode = 0

    def communicate(self, timeout=None):
        result = self._comm_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def kill(self):
        self.killed = True

    def wait(self):
        self.waited = True


class _FakeKernel32:
    def __init__(self, assign_ok=True, set_info_ok=True, open_ok=True):
        self.assign_ok = assign_ok
        self.set_info_ok = set_info_ok
        self.open_ok = open_ok
        self.calls = []
        self.closed_handles = []
        self.terminated = False
        self.last_mem_limit = None
        self.last_active_limit = None

    def CreateJobObjectW(self, a, b):
        self.calls.append("CreateJobObjectW")
        return 111

    def SetInformationJobObject(self, hjob, cls, ptr, size):
        self.calls.append(("SetInformationJobObject", hjob))
        struct_ptr = ctypes.cast(ptr, ctypes.POINTER(ws._JOBOBJECT_EXTENDED_LIMIT_INFORMATION))
        self.last_mem_limit = struct_ptr.contents.ProcessMemoryLimit
        self.last_active_limit = struct_ptr.contents.BasicLimitInformation.ActiveProcessLimit
        return 1 if self.set_info_ok else 0

    def OpenProcess(self, access, inherit, pid):
        self.calls.append(("OpenProcess", pid))
        return 222 if self.open_ok else 0

    def AssignProcessToJobObject(self, hjob, hprocess):
        self.calls.append(("AssignProcessToJobObject", hjob, hprocess))
        return 1 if self.assign_ok else 0

    def TerminateJobObject(self, hjob, code):
        self.terminated = True
        return 1

    def CloseHandle(self, h):
        self.closed_handles.append(h)
        return 1


def test_available_reflects_kernel32_presence(monkeypatch):
    monkeypatch.setattr(ws, "_kernel32", None)
    assert ws.available() is False
    monkeypatch.setattr(ws, "_kernel32", _FakeKernel32())
    assert ws.available() is True


def test_run_capped_happy_path_applies_limits_and_closes_handles(monkeypatch):
    fake_kernel = _FakeKernel32()
    monkeypatch.setattr(ws, "_kernel32", fake_kernel)
    monkeypatch.setattr(
        subprocess, "Popen",
        lambda cmd, cwd=None, **kw: _FakeProc([("STDOUT\n", "")]),
    )

    returncode, stdout, stderr, timed_out = ws.run_capped(
        ["python", "-c", "print(1)"], cwd=".", timeout_s=5, mem_limit_bytes=256 * 1024 * 1024,
    )

    assert (returncode, stdout, stderr, timed_out) == (0, "STDOUT\n", "", False)
    assert fake_kernel.last_mem_limit == 256 * 1024 * 1024
    assert fake_kernel.last_active_limit == 8
    assert ("AssignProcessToJobObject", 111, 222) in fake_kernel.calls
    # nao pode vazar handle — job (111) e process (222) fechados
    assert set(fake_kernel.closed_handles) == {111, 222}


def test_run_capped_timeout_terminates_whole_job_not_just_child(monkeypatch):
    fake_kernel = _FakeKernel32()
    monkeypatch.setattr(ws, "_kernel32", fake_kernel)
    timeout_exc = subprocess.TimeoutExpired(cmd="x", timeout=5)
    monkeypatch.setattr(
        subprocess, "Popen",
        lambda cmd, cwd=None, **kw: _FakeProc([timeout_exc, ("partial", "")]),
    )

    returncode, stdout, stderr, timed_out = ws.run_capped(
        ["python", "-c", "while True: pass"], cwd=".", timeout_s=1, mem_limit_bytes=1024,
    )

    assert timed_out is True
    assert fake_kernel.terminated is True


def test_run_capped_raises_oserror_when_assign_fails_and_kills_child(monkeypatch):
    fake_kernel = _FakeKernel32(assign_ok=False)
    monkeypatch.setattr(ws, "_kernel32", fake_kernel)
    proc_holder = {}

    def fake_popen(cmd, cwd=None, **kw):
        proc = _FakeProc([("", "")])
        proc_holder["proc"] = proc
        return proc

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    try:
        ws.run_capped(["python"], cwd=".", timeout_s=5, mem_limit_bytes=1024)
        assert False, "deveria levantar OSError"
    except OSError:
        pass

    assert proc_holder["proc"].killed is True
    assert proc_holder["proc"].waited is True


def test_run_capped_without_kernel32_raises_oserror_immediately(monkeypatch):
    monkeypatch.setattr(ws, "_kernel32", None)
    try:
        ws.run_capped(["python"], cwd=".", timeout_s=5, mem_limit_bytes=1024)
        assert False, "deveria levantar OSError sem kernel32"
    except OSError:
        pass
