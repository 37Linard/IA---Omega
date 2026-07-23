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

from config import CIRCUIT_BREAKER_DEFAULT_COOLDOWN, CIRCUIT_BREAKER_COOLDOWNS

log = logging.getLogger(__name__)

FAILURE_THRESHOLD = 3     # falhas seguidas pra abrir o circuito

_lock: threading.Lock = threading.Lock()
_state: dict[str, dict] = {}   # tool -> {"failures": int, "opened_at": float|None}


def _cooldown_for(tool: str) -> int:
    """Tool com credencial faltando (Drive, Notion...) só volta a funcionar
    quando um humano configurar — cooldown longo. Tool de rede transiente
    (busca, cotação) tende a resolver sozinha — cooldown curto. Achado
    2026-07-23: 300s fixo pra tudo desperdiçava tempo nos dois extremos."""
    return CIRCUIT_BREAKER_COOLDOWNS.get(tool, CIRCUIT_BREAKER_DEFAULT_COOLDOWN)


def _get(tool: str) -> dict:
    return _state.setdefault(tool, {"failures": 0, "opened_at": None})


def is_open(tool: str) -> tuple[bool, float]:
    """Retorna (aberto, segundos_restantes). Após o cooldown da tool, volta
    False (half-open) — deixa uma tentativa real passar pra ver se já resolveu."""
    with _lock:
        s = _get(tool)
        if s["opened_at"] is None:
            return False, 0.0
        cooldown = _cooldown_for(tool)
        elapsed = time.monotonic() - s["opened_at"]
        if elapsed >= cooldown:
            return False, 0.0
        return True, round(cooldown - elapsed, 1)


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
            cooldown = _cooldown_for(tool)
            open_now = opened is not None and (now - opened) < cooldown
            out.append({
                "tool": tool,
                "failures": s["failures"],
                "open": open_now,
                "cooldown_remaining_s": round(cooldown - (now - opened), 1) if open_now else 0.0,
            })
        return sorted(out, key=lambda x: (-x["open"], -x["failures"]))
