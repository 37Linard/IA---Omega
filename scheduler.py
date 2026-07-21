import threading
import time
import logging
from datetime import datetime

log = logging.getLogger(__name__)


def _combined_tasks(static_tasks: list) -> list[tuple[str, dict]]:
    """Junta as tarefas fixas (config.py, SCHEDULED_TASKS) com as dinâmicas
    (criadas via chat pela tool schedule_task, recarregadas do disco a cada
    chamada). Chave estável mesmo quando dinâmicas são adicionadas/removidas
    entre iterações: estáticas usam índice fixo na lista (que não muda em
    runtime), dinâmicas usam o próprio id (uuid)."""
    from tools.schedule_task_tool import load_scheduled_tasks

    combined = [(f"static_{i}", cfg) for i, cfg in enumerate(static_tasks)]
    combined += [(cfg["id"], cfg) for cfg in load_scheduled_tasks()]
    return combined


def _due_now(combined: list[tuple[str, dict]], now: datetime, ran_today: set) -> list[tuple[str, dict]]:
    """Filtra as tarefas cujo horário bate com 'now' e que ainda não rodaram hoje."""
    day_key = now.strftime("%Y-%m-%d")
    due = []
    for task_key, cfg in combined:
        key = f"{day_key}_{task_key}"
        if key in ran_today:
            continue
        if now.hour == cfg.get("hour", -1) and now.minute == cfg.get("minute", -1):
            due.append((key, cfg))
    return due


def start(agent_factory, tasks: list):
    """
    Roda tarefas agendadas em background thread.
    tasks: lista fixa de dicts com 'task', 'hour', 'minute' (e opcionalmente
    'label'), definida em config.py (SCHEDULED_TASKS). Além dessas, a cada
    iteração o loop também recarrega tools/schedule_task_tool.py — tarefas
    que o próprio agente criou via chat ("todo dia às 9h resuma as
    notícias") — sem precisar reiniciar o processo pra uma nova valer.

    Exemplo em config.py:
    SCHEDULED_TASKS = [
        {"label": "Resumo diário", "task": "pesquise as principais notícias do Brasil hoje e salve em noticias.txt", "hour": 8, "minute": 0},
    ]
    """
    def loop():
        ran_today: set = set()
        while True:
            now = datetime.now()

            for key, cfg in _due_now(_combined_tasks(tasks), now, ran_today):
                ran_today.add(key)
                label = cfg.get("label", cfg["task"][:40])
                log.info("Scheduler: iniciando '%s'", label)
                try:
                    agent  = agent_factory()
                    result = agent.run(cfg["task"])
                    log.info("Scheduler: '%s' concluído — %s", label, result[:100])
                except Exception as e:
                    log.error("Scheduler: erro em '%s': %s", label, e)

            # Limpa chaves de dias anteriores à meia-noite
            if now.hour == 0 and now.minute < 1:
                day_key = now.strftime("%Y-%m-%d")
                ran_today = {k for k in ran_today if k.startswith(day_key)}

            time.sleep(30)

    t = threading.Thread(target=loop, daemon=True, name="scheduler")
    t.start()
    log.info("Scheduler iniciado com %d tarefa(s) estática(s) + dinâmicas via chat", len(tasks))
