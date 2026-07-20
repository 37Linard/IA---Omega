"""
Circuit breaker por tool — falha repetida na MESMA tool (não no mesmo input,
isso já é MAX_TOOL_RETRIES em agent.py) abre o circuito por um tempo, evitando
gastar rede/tempo/tokens numa ferramenta que já provou estar fora do ar (ex.:
Google Drive sem credencial, LanceDB indisponível, SMTP não configurado).

Estado em memória, por processo — reinicia fechado a cada boot, o que é
correto: um restart pode ser exatamente o fix (Ollama voltou, credencial foi
adicionada). Compartilhado entre threads de propósito — se um specialist
descobrir que a tool tá fora, outro specialist paralelo (modo colaborativo)
não precisa descobrir de novo do zero.
"""
import logging
import threading
import time

log = logging.getLogger(__name__)

FAILURE_THRESHOLD = 3     # falhas seguidas pra abrir o circuito
COOLDOWN_SECONDS  = 300   # tempo aberto antes de deixar passar 1 tentativa real (half-open)

_lock: threading.Lock = threading.Lock()
_state: dict[str, dict] = {}   # tool -> {"failures": int, "opened_at": float|None}


def _get(tool: str) -> dict:
    return _state.setdefault(tool, {"failures": 0, "opened_at": None})


def is_open(tool: str) -> tuple[bool, float]:
    """Retorna (aberto, segundos_restantes). Após COOLDOWN, volta False
    (half-open) — deixa uma tentativa real passar pra ver se já resolveu."""
    with _lock:
        s = _get(tool)
        if s["opened_at"] is None:
            return False, 0.0
        elapsed = time.monotonic() - s["opened_at"]
        if elapsed >= COOLDOWN_SECONDS:
            return False, 0.0
        return True, round(COOLDOWN_SECONDS - elapsed, 1)


def record_result(tool: str, success: bool):
    with _lock:
        s = _get(tool)
        if success:
            s["failures"] = 0
            s["opened_at"] = None
            return
        s["failures"] += 1
        if s["failures"] >= FAILURE_THRESHOLD:
            s["opened_at"] = time.monotonic()
            log.warning("CIRCUIT BREAKER: '%s' aberto após %d falhas seguidas", tool, s["failures"])


def reset(tool: str = None):
    """Reset manual — útil pra testes ou pra desbloquear na mão sem reiniciar o processo."""
    with _lock:
        if tool:
            _state.pop(tool, None)
        else:
            _state.clear()


def status() -> list[dict]:
    with _lock:
        now = time.monotonic()
        out = []
        for tool, s in _state.items():
            opened = s["opened_at"]
            open_now = opened is not None and (now - opened) < COOLDOWN_SECONDS
            out.append({
                "tool": tool,
                "failures": s["failures"],
                "open": open_now,
                "cooldown_remaining_s": round(COOLDOWN_SECONDS - (now - opened), 1) if open_now else 0.0,
            })
        return sorted(out, key=lambda x: (-x["open"], -x["failures"]))
