import concurrent.futures
import json
import logging
import re
import threading

from memory import Memory

log = logging.getLogger(__name__)

SPECIALISTS = {
    "pesquisador": {
        "label": "Pesquisador",
        "tools": ["web_search", "fetch_page", "http_request", "get_currency"],
        "hint":  "pesquisa, notícia, URL, API, cotação, câmbio, moeda, dólar, euro",
    },
    "arquivos": {
        "label": "Gerenciador de Arquivos",
        "tools": ["read_file", "write_file", "list_directory", "save_note", "rag_search"],
        "hint":  "ler arquivo, criar arquivo, salvar, listar pasta, nota, PDF, documento, contrato, relatório",
    },
    "codigo": {
        "label": "Programador",
        "tools": ["run_python", "run_sql", "terminal", "git"],
        "hint":  "python, código, calcular, SQL, banco de dados, terminal, shell, git",
    },
    "computador": {
        "label": "Controlador do Computador",
        "tools": ["screenshot", "keyboard", "mouse", "clipboard", "browser"],
        "hint":  "screenshot, print, teclado, mouse, clicar, copiar, colar, browser, Chrome",
    },
    "comunicacao": {
        "label": "Comunicação",
        "tools": ["send_email", "remember_fact"],
        "hint":  "email, memorizar, lembrar, guardar fato, preferência",
    },
    "visao": {
        "label": "Visão",
        "tools": ["analyze_image", "screenshot"],
        "hint":  "analisar imagem, foto, PNG, JPG, ver imagem, descrever imagem, ler texto em imagem",
    },
    "geral": {
        "label": "Agente Geral",
        "tools": [],  # vazio = todas as tools
        "hint":  "múltiplas áreas, tarefa complexa, não se encaixa nas outras",
    },
}

SPECIALIST_PROMPTS = {
    "pesquisador": "Você é especialista em pesquisa de informações. Priorize web_search e fetch_page.",
    "arquivos":    "Você é especialista em manipulação de arquivos. Priorize read_file e write_file.",
    "codigo":      "Você é especialista em execução de código. Priorize run_python e run_sql.",
    "computador":  "Você é especialista em automação de interface. Priorize screenshot e browser.",
    "comunicacao": "Você é especialista em comunicação e memória. Use send_email e remember_fact.",
    "visao":       "Você é especialista em análise de imagens. Use analyze_image.",
    "geral":       "",
}

MAX_PARALLEL = 3  # max especialistas simultâneos


class OrchestratorAgent:
    def __init__(self, llm, all_tools: list):
        self.llm       = llm
        self.all_tools = {t.name: t for t in all_tools} if isinstance(all_tools, list) else all_tools
        self.memory    = Memory()
        self._cancel   = threading.Event()
        self._active   = []   # especialistas ativos (lista thread-safe via lock)
        self._lock     = threading.Lock()

    def cancel(self):
        self._cancel.set()
        with self._lock:
            for agent in self._active:
                agent.cancel()

    def reset_cancel(self):
        self._cancel.clear()
        with self._lock:
            self._active.clear()

    # -----------------------------------------------------------------
    # Classificação simples (um especialista)
    # -----------------------------------------------------------------
    def _classify(self, task: str) -> str:
        options = "\n".join(f"- {k}: {v['hint']}" for k, v in SPECIALISTS.items())
        prompt  = (
            f"Classifique a tarefa abaixo em UMA categoria.\n\n"
            f"Categorias:\n{options}\n\n"
            f"Tarefa: {task}\n\n"
            f"Responda APENAS com o nome exato da categoria "
            f"(pesquisador/arquivos/codigo/computador/comunicacao/visao/geral):"
        )
        result = self.llm.generate(prompt).strip().lower()
        for key in SPECIALISTS:
            if key in result:
                log.info("ORCHESTRATOR: tarefa → %s", key)
                return key
        return "geral"

    # -----------------------------------------------------------------
    # Decomposição para modo colaborativo
    # -----------------------------------------------------------------
    def _decompose_parallel(self, task: str) -> list[dict]:
        """LLM divide tarefa em subtarefas independentes com especialistas."""
        hints  = "\n".join(f"- {k}: {v['hint']}" for k, v in SPECIALISTS.items())
        prompt = (
            "Decomponha a tarefa abaixo em subtarefas INDEPENDENTES (máx 4) que podem ser executadas em paralelo.\n"
            "Para cada subtarefa, indique o especialista mais adequado.\n\n"
            f"Especialistas:\n{hints}\n\n"
            "Responda APENAS em JSON válido, sem texto adicional:\n"
            '[{"subtask": "...", "specialist": "pesquisador"}, ...]\n\n'
            f"Tarefa: {task}\n"
            "JSON:"
        )
        raw = self.llm.generate(prompt)
        m   = re.search(r'\[.*?\]', raw, re.DOTALL)
        if not m:
            return [{"subtask": task, "specialist": self._classify(task)}]
        try:
            items = json.loads(m.group())
            valid = [i for i in items
                     if isinstance(i, dict) and "subtask" in i and "specialist" in i
                     and i["specialist"] in SPECIALISTS]
            return valid or [{"subtask": task, "specialist": "geral"}]
        except Exception:
            return [{"subtask": task, "specialist": "geral"}]

    # -----------------------------------------------------------------
    # Detecção de tarefa multi-domínio
    # -----------------------------------------------------------------
    def _needs_collaboration(self, task: str) -> bool:
        t = task.lower()
        seq_words = [" e ", " depois ", " então ", " em seguida ", " também "]
        if not any(w in t for w in seq_words) or len(task) < 30:
            return False
        # Conta domínios distintos detectados
        domains = sum(
            any(kw.strip() in t for kw in spec["hint"].split(",")[:2])
            for spec in SPECIALISTS.values()
            if spec["hint"]
        )
        return domains >= 3

    # -----------------------------------------------------------------
    # Criação de especialista
    # -----------------------------------------------------------------
    def _create_specialist(self, specialist_name: str):
        from agent import ReActAgent

        spec  = SPECIALISTS[specialist_name]
        tools = ([self.all_tools[t] for t in spec["tools"] if t in self.all_tools]
                 if spec["tools"] else list(self.all_tools.values()))

        agent = ReActAgent(
            llm=self.llm,
            tools=tools,
            specialist_context=SPECIALIST_PROMPTS.get(specialist_name, ""),
        )
        agent._cancel = self._cancel
        if "remember_fact" in agent.tools:
            agent.tools["remember_fact"].memory = self.memory
        return agent

    # -----------------------------------------------------------------
    # Modo simples: um especialista
    # -----------------------------------------------------------------
    def _run_single(self, task: str, step_callback=None) -> str:
        def emit(data):
            if step_callback:
                step_callback(data)

        specialist_name = self._classify(task)
        spec_label      = SPECIALISTS[specialist_name]["label"]
        emit({"type": "thought", "content": f"Especialista: {spec_label}"})
        log.info("ORCHESTRATOR → %s", spec_label)

        agent = self._create_specialist(specialist_name)
        with self._lock:
            self._active.append(agent)
        try:
            return agent.run(task, max_steps=15, step_callback=step_callback)
        finally:
            with self._lock:
                if agent in self._active:
                    self._active.remove(agent)

    # -----------------------------------------------------------------
    # Modo colaborativo: especialistas em paralelo
    # -----------------------------------------------------------------
    def _run_collaborative(self, task: str, step_callback=None) -> str:
        def emit(data):
            if step_callback:
                step_callback(data)

        emit({"type": "thought", "content": "Modo colaborativo — decompondo para especialistas paralelos..."})

        assignments = self._decompose_parallel(task)
        if len(assignments) <= 1:
            return self._run_single(task, step_callback)

        plan = "\n".join(
            f"{i+1}. [{a['specialist']}] {a['subtask']}"
            for i, a in enumerate(assignments)
        )
        emit({"type": "thought", "content": f"Plano colaborativo:\n{plan}"})

        results  = [None] * len(assignments)
        res_lock = threading.Lock()

        def run_one(idx: int, assignment: dict):
            if self._cancel.is_set():
                return
            name    = assignment["specialist"]
            label   = SPECIALISTS[name]["label"]
            subtask = assignment["subtask"]

            emit({"type": "agent_status", "agent": label, "status": "running", "subtask": subtask})

            agent = self._create_specialist(name)
            with self._lock:
                self._active.append(agent)

            def sub_cb(data):
                if data.get("type") in ("thought", "action", "observation", "error"):
                    emit({**data, "agent": label})

            try:
                result = agent.run(subtask, max_steps=8, step_callback=sub_cb)
            except Exception as e:
                result = f"Erro em {label}: {e}"
            finally:
                with self._lock:
                    if agent in self._active:
                        self._active.remove(agent)

            emit({"type": "agent_status", "agent": label, "status": "done", "result": result[:200]})
            with res_lock:
                results[idx] = result

        workers = min(len(assignments), MAX_PARALLEL)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(run_one, i, a) for i, a in enumerate(assignments)]
            concurrent.futures.wait(futs)

        if self._cancel.is_set():
            return "Cancelado."

        valid = [(assignments[i]["subtask"], r) for i, r in enumerate(results) if r]
        if not valid:
            return "Nenhum resultado obtido."
        if len(valid) == 1:
            return valid[0][1]

        emit({"type": "thought", "content": "Agregando resultados dos especialistas..."})
        agg_prompt = (
            f"Tarefa original: {task}\n\n"
            "Resultados dos especialistas:\n" +
            "\n\n".join(f"[{st}]:\n{r[:400]}" for st, r in valid) +
            "\n\nCombine os resultados em uma resposta final coesa e completa:\nFinal Answer:"
        )
        final = self.llm.generate(agg_prompt)
        emit({"type": "final", "content": final})
        return final

    # -----------------------------------------------------------------
    # Entrada principal
    # -----------------------------------------------------------------
    def run(self, task: str, max_steps: int = 15, step_callback=None) -> str:
        if self._cancel.is_set():
            return "Cancelado."

        if self._needs_collaboration(task):
            return self._run_collaborative(task, step_callback)
        return self._run_single(task, step_callback)
