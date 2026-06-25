import threading
import time
import logging
from datetime import datetime

log = logging.getLogger(__name__)


def start(agent_factory, tasks: list):
    """
    Roda tarefas agendadas em background thread.
    tasks: lista de dicts com 'task', 'hour', 'minute' (e opcionalmente 'label').

    Exemplo em config.py:
    SCHEDULED_TASKS = [
        {"label": "Resumo diário", "task": "pesquise as principais notícias do Brasil hoje e salve em noticias.txt", "hour": 8, "minute": 0},
    ]
    """
    if not tasks:
        return

    def loop():
        ran_today: set = set()
        while True:
            now     = datetime.now()
            day_key = now.strftime("%Y-%m-%d")

            for i, cfg in enumerate(tasks):
                key = f"{day_key}_{i}"
                if key in ran_today:
                    continue
                if now.hour == cfg.get("hour", -1) and now.minute == cfg.get("minute", -1):
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
                ran_today = {k for k in ran_today if k.startswith(day_key)}

            time.sleep(30)

    t = threading.Thread(target=loop, daemon=True, name="scheduler")
    t.start()
    log.info("Scheduler iniciado com %d tarefa(s)", len(tasks))
