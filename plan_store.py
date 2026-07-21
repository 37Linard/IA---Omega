"""
Plan Store — persiste em disco o plano de uma tarefa composta
(Plan-then-Execute, ver agent.py:_plan) passo a passo, pra sobreviver a um
crash do processo (kill -9, OOM, queda de energia) no meio da execução.

Se o servidor cair no passo 3 de 5, o arquivo fica com status "running" —
na próxima vez que o agente reconhecer a MESMA tarefa (texto idêntico) ou o
usuário pedir explicitamente pra continuar, retoma do passo 4 em vez de
recomeçar do zero (ver agent.py:_find_resumable_plan).

Cancelamento intencional e conclusão normal apagam o arquivo via finish() —
só sobra em disco quando o processo morreu sem chance de rodar esse
cleanup, que é exatamente o sinal de "precisa retomar". Sem filtro por
session_id de propósito: um crash mata a conexão WS também, então a
retomada sempre acontece a partir de uma sessão nova.
"""
import glob
import json
import logging
import os
import uuid
from datetime import datetime

log = logging.getLogger(__name__)

PLANS_DIR = os.path.join(os.path.dirname(__file__), "workspace", "plans")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def _path(plan_id: str) -> str:
    return os.path.join(PLANS_DIR, f"{plan_id}.json")


def save(plan_id: str, task: str, steps: list, context: dict, current_index: int = 0,
         session_id: str = "") -> None:
    os.makedirs(PLANS_DIR, exist_ok=True)
    now = datetime.now().isoformat()
    data = {
        "id": plan_id,
        "task": task,
        "steps": steps,
        "context": context,
        "current_index": current_index,
        "status": "running",
        "session_id": session_id,
        "created": now,
        "updated": now,
    }
    with open(_path(plan_id), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def update_progress(plan_id: str, current_index: int, context: dict) -> None:
    p = _path(plan_id)
    if not os.path.exists(p):
        return
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log.debug("plan_store.update_progress: %s", e)
        return
    data["current_index"] = current_index
    data["context"]       = context
    data["updated"]       = datetime.now().isoformat()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def finish(plan_id: str) -> None:
    """Conclusão normal ou cancelamento — remove o arquivo, nada a retomar."""
    try:
        os.remove(_path(plan_id))
    except FileNotFoundError:
        pass


def find_incomplete() -> dict | None:
    """Retorna o plano 'running' mais recente (sobrevivente de um crash), ou None."""
    os.makedirs(PLANS_DIR, exist_ok=True)
    candidates = []
    for fp in glob.glob(os.path.join(PLANS_DIR, "*.json")):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if data.get("status") == "running":
            candidates.append(data)
    if not candidates:
        return None
    candidates.sort(key=lambda d: d.get("updated", ""), reverse=True)
    return candidates[0]
