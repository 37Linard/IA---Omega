"""
Eval harness — roda as golden tasks (eval/golden_tasks.py) contra o agente de
verdade (Ollama tem que estar rodando) e reporta pass/fail. Pensado pra rodar
ANTES de trocar OLLAMA_MODEL/SPECIALIST_MODELS ou mexer no SYSTEM_PROMPT —
pega regressão que só aparece com o modelo real, que os testes mockados
(pytest) não pegam.

Uso:
    python eval_harness.py                    # usa OLLAMA_MODEL de config.py
    python eval_harness.py --model llama3.2:3b # testa um modelo candidato sem editar config.py
    python eval_harness.py --task python_arithmetic  # roda só uma golden task

Isola memória/perfil/audit num diretório de scratch — nunca toca
workspace/agent_memory.json/user_profile.json/audit.db reais.
"""
import argparse
import concurrent.futures
import os
import re
import sys
import tempfile
import time

# Console do Windows costuma estar em cp1252, que não cobre boa parte do
# unicode que pode aparecer em resposta de LLM ou nos próprios prints do
# harness — sem isso, um print com o caractere errado derruba o script.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _isolate_state(scratch_dir: str):
    """Redireciona os arquivos de estado persistente pro scratch_dir ANTES de
    qualquer Memory()/UserProfile()/KnowledgeGraph() ser instanciado — evita que
    rodar o harness polua a memória/perfil/audit reais do usuário."""
    os.makedirs(scratch_dir, exist_ok=True)
    import memory as memory_mod
    import user_profile as profile_mod
    import audit as audit_mod
    import knowledge_graph as kg_mod

    memory_mod.MEMORY_FILE       = os.path.join(scratch_dir, "agent_memory.json")
    memory_mod.LANCE_MEMORY_DIR  = os.path.join(scratch_dir, "lance_memory_db")
    memory_mod.BACKUP_DIR        = os.path.join(scratch_dir, "backups")
    profile_mod.PROFILE_FILE     = os.path.join(scratch_dir, "user_profile.json")
    audit_mod.AUDIT_DB           = os.path.join(scratch_dir, "audit.db")
    kg_mod.GRAPH_FILE            = os.path.join(scratch_dir, "knowledge_graph.json")


_ACTION_RE = re.compile(r"^(\w+)\(")


def _run_task(orchestrator, task_def: dict) -> dict:
    events = []

    def collect(ev):
        events.append(ev)

    t0 = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(orchestrator.run, task_def["task"], 0, collect)
        try:
            answer = future.result(timeout=task_def.get("max_seconds", 60))
        except concurrent.futures.TimeoutError:
            orchestrator.cancel(reason="eval_harness timeout")
            answer = None
    elapsed = time.monotonic() - t0

    tools_called = set()
    for ev in events:
        if ev.get("type") == "action":
            m = _ACTION_RE.match(ev.get("content", ""))
            if m:
                tools_called.add(m.group(1))

    failures = []
    if answer is None:
        failures.append(f"timeout após {task_def.get('max_seconds', 60)}s")
    else:
        answer_l = answer.lower()
        must_contain = task_def.get("must_contain") or []
        if must_contain and not any(s.lower() in answer_l for s in must_contain):
            failures.append(f"esperava alguma de {must_contain} na resposta, não achou")
        for s in task_def.get("must_not_contain", []):
            if s.lower() in answer_l:
                failures.append(f"resposta contém '{s}' (não deveria)")

    expected_tools = task_def.get("expected_tools") or []
    if expected_tools and not (tools_called & set(expected_tools)):
        failures.append(f"esperava chamar uma de {expected_tools}, tools chamadas: {sorted(tools_called) or '[]'}")
    forbidden = set(task_def.get("forbidden_tools", [])) & tools_called
    if forbidden:
        failures.append(f"chamou tool proibida: {sorted(forbidden)}")

    return {
        "id": task_def["id"],
        "passed": not failures,
        "failures": failures,
        "elapsed": round(elapsed, 1),
        "tools_called": sorted(tools_called),
        "answer_preview": (answer or "")[:150],
    }


def main():
    parser = argparse.ArgumentParser(description="Eval harness — golden tasks contra o agente real")
    parser.add_argument("--model", default=None, help="override de OLLAMA_MODEL só pra este run")
    parser.add_argument("--task", default=None, help="roda só a golden task com esse id")
    args = parser.parse_args()

    scratch_dir = os.path.join(tempfile.gettempdir(), "ia_eval_harness")
    _isolate_state(scratch_dir)

    if args.model:
        os.environ["FALLBACK_MODEL"] = ""  # não mascara falha do modelo candidato com fallback

    from eval.golden_tasks import GOLDEN_TASKS
    from llm import OllamaLLM
    from tool_loader import load_tools
    from orchestrator import OrchestratorAgent
    from config import OLLAMA_MODEL

    model = args.model or OLLAMA_MODEL
    tasks = GOLDEN_TASKS if not args.task else [t for t in GOLDEN_TASKS if t["id"] == args.task]
    if not tasks:
        print(f"Nenhuma golden task com id '{args.task}'.")
        sys.exit(2)

    print(f"Eval harness — modelo: {model} — {len(tasks)} golden task(s)\n")

    llm          = OllamaLLM(model=model)
    all_tools    = load_tools()
    orchestrator = OrchestratorAgent(llm, all_tools, session_id="eval_harness")

    results = []
    for task_def in tasks:
        print(f"[{task_def['id']}] rodando...", flush=True)
        result = _run_task(orchestrator, task_def)
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} — {result['elapsed']}s — tools: {result['tools_called']}")
        for f in result["failures"]:
            print(f"    - {f}")
        print()

    passed = sum(1 for r in results if r["passed"])
    print(f"==== {passed}/{len(results)} passou (modelo: {model}) ====")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
