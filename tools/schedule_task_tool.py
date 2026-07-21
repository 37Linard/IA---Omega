"""
Tool que deixa o próprio agente criar/listar/remover tarefas agendadas
(ex: usuário pede "todo dia às 9h resuma as notícias" em conversa normal —
o agente reconhece isso como pedido de agendamento e chama esta tool).

Persiste em workspace/scheduled_tasks.json — separado de SCHEDULED_TASKS
(config.py), que continua existindo pras tarefas fixas definidas por código.
scheduler.py lê os dois: config.py pras estáticas, este arquivo pras
criadas via chat, recarregando o arquivo a cada 30s (sem precisar reiniciar
o processo pra uma tarefa nova entrar em vigor).
"""
import json
import logging
import os
import uuid
from datetime import datetime

log = logging.getLogger(__name__)

TASKS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace", "scheduled_tasks.json")


def load_scheduled_tasks() -> list:
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning("schedule_task_tool: falha lendo %s: %s", TASKS_FILE, e)
    return []


def _save(tasks: list) -> None:
    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


class ScheduleTaskTool:
    name = "schedule_task"
    description = (
        "Cria, lista ou remove tarefas que o agente executa sozinho todo dia, num "
        "horário fixo, sem o usuário precisar pedir de novo (ex: 'todo dia às 9h "
        "resuma as notícias', 'toda manhã às 7h me dê o preço do bitcoin'). "
        "Input pra criar: {'action': 'create', 'task': 'descrição do que executar', "
        "'hour': 9, 'minute': 0, 'label': 'opcional'}. "
        "Input pra listar: {'action': 'list'}. "
        "Input pra remover: {'action': 'remove', 'id': 'id retornado por create/list'}."
    )

    def run(self, input_data: dict) -> str:
        action = (input_data.get("action") or "create").strip().lower()

        if action == "list":
            tasks = load_scheduled_tasks()
            if not tasks:
                return "Nenhuma tarefa agendada."
            return "\n".join(
                f"- [{t['id']}] {t.get('label', t['task'][:40])} — todo dia às "
                f"{t['hour']:02d}:{t['minute']:02d} → \"{t['task']}\""
                for t in tasks
            )

        if action == "remove":
            tid = str(input_data.get("id", "")).strip()
            if not tid:
                return "Erro: 'id' obrigatório pra remover — use action 'list' pra ver os ids."
            tasks  = load_scheduled_tasks()
            before = len(tasks)
            tasks  = [t for t in tasks if t["id"] != tid]
            if len(tasks) == before:
                return f"Erro: nenhuma tarefa agendada com id '{tid}'."
            _save(tasks)
            return f"Tarefa '{tid}' removida do agendamento."

        if action != "create":
            return f"Erro: action '{action}' inválida. Use 'create', 'list' ou 'remove'."

        task_desc = (input_data.get("task") or "").strip()
        if not task_desc:
            return "Erro: 'task' obrigatório — descreva o que deve ser executado todo dia."
        try:
            hour   = int(input_data.get("hour"))
            minute = int(input_data.get("minute", 0))
        except (TypeError, ValueError):
            return "Erro: 'hour' (0-23) obrigatório e numérico."
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return "Erro: 'hour' deve ser 0-23 e 'minute' 0-59."

        tasks = load_scheduled_tasks()
        new_task = {
            "id":      uuid.uuid4().hex[:8],
            "label":   (input_data.get("label") or task_desc[:40]).strip(),
            "task":    task_desc,
            "hour":    hour,
            "minute":  minute,
            "created": datetime.now().isoformat(),
        }
        tasks.append(new_task)
        _save(tasks)
        return (
            f"Tarefa agendada com sucesso: todo dia às {hour:02d}:{minute:02d}, "
            f"\"{task_desc}\" (id: {new_task['id']})."
        )
