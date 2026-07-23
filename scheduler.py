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


def _run_nightly_eval():
    """Roda eval_harness.py como SUBPROCESSO — nunca importado/chamado
    in-process, porque eval_harness._isolate_state() redireciona os globais
    de módulo (memory.MEMORY_FILE, audit.AUDIT_DB, tracing.TRACE_DB) pro
    scratch dir; se rodasse na mesma thread/processo do servidor, um usuário
    real conversando durante o eval teria a sessão gravada no lugar errado."""
    import subprocess
    import sys
    import os

    project_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        result = subprocess.run(
            [sys.executable, "eval_harness.py"],
            cwd=project_dir, capture_output=True, text=True, timeout=900,
        )
        passed = result.returncode == 0
        tail = (result.stdout or "")[-2000:]
        log.info("Eval noturno: %s\n%s", "PASSOU" if passed else "FALHOU", tail)
        if not passed:
            _notify_eval_failure(tail)
    except subprocess.TimeoutExpired:
        log.error("Eval noturno: excedeu 900s, abortado.")
    except Exception as e:
        log.error("Eval noturno: erro ao rodar — %s", e)


def _notify_eval_failure(output_tail: str):
    """Best-effort — se discord_notify não estiver configurado, só loga (já
    logou acima); não deixa a falha de notificação mascarar a falha do eval."""
    try:
        from tools.discord_notify_tool import DiscordNotifyTool
        preview = output_tail[-1500:]
        DiscordNotifyTool().run({
            "message": f"⚠️ Eval noturno falhou — possível regressão de modelo/prompt.\n```\n{preview}\n```"
        })
    except Exception as e:
        log.warning("Eval noturno: falha ao notificar Discord — %s", e)


def start_nightly_eval(hour: int, minute: int):
    """Roda eval_harness.py 1x/dia no horário configurado. Complementa o hook
    pre-push (que só roda quando arquivo de comportamento muda) — pega
    regressão de qualidade que aparece só com o Ollama real, mesmo sem
    nenhum código ter mudado (ex.: troca de versão do modelo no Ollama)."""
    def loop():
        ran_today = None
        while True:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            if now.hour == hour and now.minute == minute and ran_today != today:
                ran_today = today
                log.info("Eval noturno: iniciando (%02d:%02d)...", hour, minute)
                _run_nightly_eval()
            time.sleep(30)

    t = threading.Thread(target=loop, daemon=True, name="nightly_eval")
    t.start()
    log.info("Eval noturno agendado pra %02d:%02d", hour, minute)
