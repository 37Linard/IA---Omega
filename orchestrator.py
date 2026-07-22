import concurrent.futures
import json
import logging
import re
import threading

from memory import Memory

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Runtime model overrides — sobrepõem config.py sem reiniciar o servidor
# ---------------------------------------------------------------------------
_runtime_models: dict[str, str] = {}


def get_specialist_model(specialist: str) -> str:
    from config import SPECIALIST_MODELS, OLLAMA_MODEL
    return (
        _runtime_models.get(specialist)
        or SPECIALIST_MODELS.get(specialist, "")
        or OLLAMA_MODEL
    )


def set_specialist_model(specialist: str, model: str) -> None:
    _runtime_models[specialist] = model
    log.info("SPECIALIST MODEL: %s → %s", specialist, model)


def get_manager_model() -> str:
    from config import MANAGER_MODEL, OLLAMA_MODEL
    return MANAGER_MODEL or OLLAMA_MODEL


def list_specialist_models() -> dict[str, str]:
    return {name: get_specialist_model(name) for name in SPECIALISTS}

SPECIALISTS = {
    "pesquisador": {
        "label": "Pesquisador",
        "tools": ["web_search", "fetch_page", "http_request", "get_currency", "get_crypto", "rag_search"],
        "hint":  "pesquisa, notícia, URL, API, cotação, câmbio, moeda, dólar, euro, bitcoin, cripto, criptomoeda, ethereum, verificar fatos",
    },
    "arquivos": {
        "label": "Gerenciador de Arquivos",
        "tools": ["read_file", "write_file", "list_directory", "save_note", "rag_search", "read_spreadsheet"],
        "hint":  "ler arquivo, criar arquivo, salvar, listar pasta, nota, PDF, documento, contrato, relatório, planilha, Excel, CSV",
    },
    "codigo": {
        "label": "Programador",
        "tools": ["run_python", "run_sql", "terminal", "git", "read_file", "write_file", "generate_chart"],
        "hint":  "python, código, calcular, SQL, banco de dados, terminal, shell, git, programar, refatorar, bug, algoritmo, gráfico",
    },
    "computador": {
        "label": "Controlador do Computador",
        "tools": ["screenshot", "keyboard", "mouse", "clipboard", "browser"],
        "hint":  "screenshot, print, teclado, mouse, clicar, copiar, colar, browser, Chrome, automação",
    },
    "comunicacao": {
        "label": "Comunicação",
        "tools": ["send_email", "remember_fact", "notion", "slack", "schedule_task"],
        "hint":  "email, memorizar, lembrar, guardar fato, preferência, Notion, Slack, mensagem, "
                 "agendar, agendamento, agenda, lembrete, todo dia, toda manhã, todos os dias, diariamente",
    },
    "visao": {
        "label": "Visão",
        "tools": ["analyze_image", "screenshot", "generate_image"],
        "hint":  "analisar imagem, foto, PNG, JPG, ver imagem, descrever imagem, ler texto em imagem, diagrama, gerar imagem, criar imagem, desenhar, ilustração, arte",
    },
    "professor": {
        "label": "Professor",
        "tools": ["web_search", "fetch_page", "run_python", "write_file", "save_note", "remember_fact", "read_file"],
        "hint":  "aprender, ensinar, explicar, exercício, plano de estudo, tutorial, como funciona, o que é, me ensine, me explique, dúvida, estudo, curso, aula",
    },
    "dados": {
        "label": "Analista de Dados",
        "tools": ["read_spreadsheet", "run_python", "run_sql", "generate_chart", "read_file", "write_file", "rag_search"],
        "hint":  "analisar dados, planilha, gráfico, estatística, CSV, Excel, visualização, dashboard, relatório de dados",
    },
    "geral": {
        "label": "Agente Geral",
        "tools": [],
        "hint":  "múltiplas áreas, tarefa complexa, não se encaixa nas outras",
    },
}

SPECIALIST_PROMPTS = {
    "pesquisador": (
        "Você é especialista em pesquisa. Busque informações atualizadas, cite fontes, "
        "compare múltiplas perspectivas e verifique fatos. Priorize web_search e fetch_page."
    ),
    "arquivos": (
        "Você é especialista em gestão de arquivos e documentos. "
        "Leia, crie e organize arquivos com eficiência. Priorize read_file e write_file."
    ),
    "codigo": (
        "Você é especialista em programação. Gere código limpo, explique soluções, "
        "detecte bugs, sugira melhorias e suporte múltiplas linguagens. "
        "Priorize run_python e run_sql. Para visualizações, use generate_chart."
    ),
    "computador": (
        "Você é especialista em automação de interface. "
        "Controle o computador com precisão. Priorize screenshot e browser."
    ),
    "comunicacao": (
        "Você é especialista em comunicação e integração. "
        "Gerencie emails, memorize preferências e integre com Notion e Slack."
    ),
    "visao": (
        "Você é especialista em análise visual. "
        "Analise imagens, diagramas, gráficos e screenshots. Use analyze_image."
    ),
    "professor": (
        "Você é um professor especializado e tutor adaptativo. "
        "MODO PROFESSOR ATIVO:\n"
        "- Ensine passo a passo com exemplos práticos\n"
        "- Crie exercícios relevantes\n"
        "- Adapte a explicação ao nível do aluno (veja perfil do usuário)\n"
        "- Identifique dificuldades e ajuste abordagem\n"
        "- Gere planos de estudo estruturados quando solicitado\n"
        "- Use analogias para conceitos abstratos\n"
        "- Confirme compreensão antes de avançar\n"
        "Ao final de explicações, sugira o próximo passo de aprendizado."
    ),
    "dados": (
        "Você é especialista em análise de dados. "
        "Leia planilhas, execute análises estatísticas, gere visualizações e "
        "apresente insights de forma clara. Priorize read_spreadsheet e generate_chart."
    ),
    "geral": "",
}

MAX_PARALLEL = 3  # max especialistas simultâneos

_SEQ_WORDS = (" e ", " depois ", " então ", " em seguida ", " também ")


def domain_hits(task: str) -> set[str]:
    """Especialistas cujo dominio aparece na tarefa.
    Usa o radical (5 chars) da ultima palavra de cada keyword do hint —
    tolera conjugacoes verbais (pesquisa/pesquisar/pesquise/pesquisando)
    em vez de exigir substring exata."""
    t = task.lower()
    hits = set()
    for key, spec in SPECIALISTS.items():
        hint = spec.get("hint", "")
        if not hint:
            continue
        for kw in hint.split(","):
            kw = kw.strip()
            if not kw:
                continue
            core = kw.split()[-1] if " " in kw else kw
            stem = core[:5] if len(core) > 5 else core
            if stem and stem in t:
                hits.add(key)
                break
    return hits


def tools_for_domains(domains: set[str]) -> list[str]:
    """União ordenada das tools de cada especialista em `domains` — usada pra
    liberar só as ferramentas dos domínios detectados numa tarefa composta,
    em vez do toolset inteiro do sistema (least privilege)."""
    return sorted({t for d in domains for t in SPECIALISTS.get(d, {}).get("tools", [])})


def is_multi_domain(task: str, min_domains: int = 2) -> bool:
    """Detecta tarefa composta (multiplos dominios sequenciais).
    min_domains=3 → modo colaborativo (especialistas paralelos).
    min_domains=2 → plan-then-execute single-agent com toolset completo."""
    if len(task) < 30:
        return False
    t = task.lower()
    if not any(w in t for w in _SEQ_WORDS):
        return False
    return len(domain_hits(task)) >= min_domains


class OrchestratorAgent:
    _llm_cache: dict[str, object] = {}  # model_name → OllamaLLM (shared across instances)

    def __init__(self, llm, all_tools: list, session_id: str = ""):
        from user_profile import UserProfile
        self.llm            = llm
        self.all_tools      = {t.name: t for t in all_tools} if isinstance(all_tools, list) else all_tools
        self.memory         = Memory()
        self.profile        = UserProfile()
        self.session_id     = session_id
        self._cancel        = threading.Event()
        self._cancel_reason = "usuário"
        self._active        = []
        self._lock          = threading.Lock()
        # Registra o llm padrão no cache
        OrchestratorAgent._llm_cache[llm.model] = llm

    def _get_llm(self, model: str):
        """Retorna OllamaLLM cacheado para o model. Cria se necessário."""
        if model not in OrchestratorAgent._llm_cache:
            from llm import OllamaLLM
            OrchestratorAgent._llm_cache[model] = OllamaLLM(model=model)
            log.info("LLM cache MISS — criando OllamaLLM(%s)", model)
        return OrchestratorAgent._llm_cache[model]

    def cancel(self, reason: str = "usuário"):
        self._cancel_reason = reason
        self._cancel.set()
        with self._lock:
            for agent in self._active:
                agent.cancel(reason=reason)

    def reset_cancel(self):
        self._cancel.clear()
        self._cancel_reason = "usuário"
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
        manager_llm = self._get_llm(get_manager_model())
        result = manager_llm.generate(prompt).strip().lower()
        for key in SPECIALISTS:
            if key in result:
                log.info("ORCHESTRATOR: tarefa → %s (model=%s)", key, manager_llm.model)
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
        raw = self._get_llm(get_manager_model()).generate(prompt)
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
        return is_multi_domain(task, min_domains=3)

    # -----------------------------------------------------------------
    # Criação de especialista
    # -----------------------------------------------------------------
    def _create_specialist(self, specialist_name: str, tool_names: list[str] = None):
        """tool_names=None -> toolset padrao do especialista (ou tudo se for 'geral',
        que nao tem categoria propria). tool_names explicito -> restringe a essa lista
        (usado pra liberar so os dominios detectados na tarefa, nao a ferramenta inteira)."""
        from agent import ReActAgent

        spec = SPECIALISTS[specialist_name]
        if tool_names is not None:
            tools = [self.all_tools[t] for t in tool_names if t in self.all_tools]
        elif not spec["tools"]:
            tools = list(self.all_tools.values())
        else:
            tools = [self.all_tools[t] for t in spec["tools"] if t in self.all_tools]

        model          = get_specialist_model(specialist_name)
        specialist_llm = self._get_llm(model)

        agent = ReActAgent(
            llm=specialist_llm,
            tools=tools,
            specialist_context=SPECIALIST_PROMPTS.get(specialist_name, ""),
            session_id=self.session_id,
            memory=self.memory,
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
        spec_model      = get_specialist_model(specialist_name)
        hits            = domain_hits(task)
        # Aqui só decide AMPLIAR o toolset de UM especialista já escolhido — baixo
        # risco (pior caso: ganha uma tool que não usa). Por isso não exige palavra
        # de sequência como is_multi_domain (essa exige, porque decide reestruturar
        # a tarefa inteira em Plan-then-Execute — risco maior de forçar passos numa
        # tarefa simples). Sem isso, "Agende: todo dia às 9h me avise o preço do
        # bitcoin" classificava como Pesquisador (por causa de "bitcoin") mas sem
        # schedule_task disponível (só em "comunicacao") — o modelo inventava uma
        # tool ('set_daily_reminder') que não existe.
        multi_domain    = len(hits) >= 2
        emit({"type": "thought", "content": f"Especialista: {spec_label} · {spec_model}"})

        tool_names = None
        if multi_domain and specialist_name != "geral":
            # Só libera as ferramentas dos domínios realmente detectados na tarefa
            # (least privilege) em vez da lista inteira de tools do sistema — o
            # especialista continua sem acesso a terminal/git/email só porque a
            # tarefa também mencionou "arquivo".
            hits = hits | {specialist_name}
            tool_names = tools_for_domains(hits)
            emit({
                "type": "thought",
                "content": f"Tarefa multi-domínio ({', '.join(sorted(hits))}) — liberando ferramentas desses domínios: {', '.join(tool_names)}",
            })
        elif multi_domain:
            emit({"type": "thought", "content": "Tarefa multi-domínio — Agente Geral já tem acesso a todas as ferramentas"})

        log.info("ORCHESTRATOR → %s (model=%s, tool_names=%s)", spec_label, spec_model, tool_names)

        if spec_model not in OrchestratorAgent._llm_cache:
            emit({"type": "thought", "content": f"Carregando modelo '{spec_model}'..."})

        agent = self._create_specialist(specialist_name, tool_names=tool_names)
        with self._lock:
            self._active.append(agent)
        try:
            return agent.run(task, step_callback=step_callback)
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
        emit({
            "type": "workflow_plan",
            "task": task,
            "nodes": [
                {"id": i, "specialist": a["specialist"], "label": SPECIALISTS[a["specialist"]]["label"], "subtask": a["subtask"]}
                for i, a in enumerate(assignments)
            ],
        })

        results  = [None] * len(assignments)
        res_lock = threading.Lock()

        def run_one(idx: int, assignment: dict):
            if self._cancel.is_set():
                return
            name    = assignment["specialist"]
            label   = SPECIALISTS[name]["label"]
            subtask = assignment["subtask"]

            spec_model = get_specialist_model(name)
            emit({"type": "agent_status", "id": idx, "agent": f"{label}·{spec_model}", "status": "running", "subtask": subtask})

            agent = self._create_specialist(name)
            with self._lock:
                self._active.append(agent)

            def sub_cb(data):
                if data.get("type") in ("thought", "action", "observation", "error"):
                    emit({**data, "agent": label})

            error = False
            try:
                result = agent.run(subtask, max_steps=8, step_callback=sub_cb)
            except Exception as e:
                result = f"Erro em {label}: {e}"
                error = True
            finally:
                with self._lock:
                    if agent in self._active:
                        self._active.remove(agent)

            emit({"type": "agent_status", "id": idx, "agent": label, "status": "error" if error else "done", "result": result[:200]})
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

        emit({"type": "agent_status", "id": "aggregate", "agent": "Agregador", "status": "running"})
        emit({"type": "thought", "content": "Agregando resultados dos especialistas..."})
        agg_prompt = (
            f"Tarefa original: {task}\n\n"
            "Resultados dos especialistas:\n" +
            "\n\n".join(f"[{st}]:\n{r[:400]}" for st, r in valid) +
            "\n\nCombine os resultados em uma resposta final coesa e completa:\nFinal Answer:"
        )
        final = self.llm.generate(agg_prompt)
        emit({"type": "agent_status", "id": "aggregate", "agent": "Agregador", "status": "done", "result": final[:200]})
        emit({"type": "final", "content": final})
        return final

    # -----------------------------------------------------------------
    # Modo conversa — bypass total (sem LLM de classificação)
    # -----------------------------------------------------------------
    _CONV_RE = re.compile(
        r"^(oi|olá|ola|hey|e aí|e ai|bom dia|boa tarde|boa noite|"
        r"tudo bem|tudo bom|como vai|como você está|como voce ta|como vc|"
        r"obrigad|valeu|vlw|brigad|"
        r"o que você acha|o que voce acha|qual (sua|tua) opini|"
        r"me (explica|conta|fala|diz)|explique|"
        r"quem é você|quem e voce|você pode|voce pode|pode me|"
        r"o que (é |sao |são |significa)|qual (a diferença|é a diferença)|"
        r"qual a diferença|diferença entre|compare |compara )",
        re.IGNORECASE,
    )
    _TASK_KW = frozenset([
        "pesquisa", "busca", "busque", "procure", "encontre", "acesse",
        "abra", "execute", "rode", "crie", "gere", "faça", "escreva",
        "salva", "salve", "lista", "leia", "analise", "calcule",
        "cotação", "preço", "bitcoin", "dólar", "euro", "clima", "tempo",
        "arquivo", "pasta", "código", "script", "terminal", "git",
        "email", "slack", "notion", "planilha", "banco de dados", "sql",
        "screenshot", "captura", "site", "url", "http",
    ])

    def _is_conversational(self, task: str) -> bool:
        t = task.strip()
        if len(t) > 200:
            return False
        tl = t.lower()
        if any(kw in tl for kw in self._TASK_KW):
            return False
        return bool(self._CONV_RE.match(t))

    def _run_conversational(self, task: str, step_callback=None) -> str:
        from datetime import datetime

        def emit(data):
            if step_callback:
                step_callback(data)

        self.profile.observe_message(task)
        self.profile.increment_interactions()

        now     = datetime.now().strftime("%d/%m/%Y %H:%M, %A")
        profile = self.profile.get_system_context()
        conv    = self.memory.get_context(task, session_id=self.session_id)

        prompt = (
            f"Você é uma IA pessoal com personalidade calorosa, curiosa e bem-humorada.\n"
            f"Data/hora: {now}\n"
            f"{profile}\n"
            f"{conv}\n"
            f"Responda de forma natural e humana. Seja breve se a mensagem for simples. "
            f"Sem listas desnecessárias. Sem mencionar ferramentas.\n\n"
            f"Usuário: {task}\n"
            f"Você:"
        )

        resposta = ""

        def on_token(tok):
            nonlocal resposta
            resposta += tok
            emit({"type": "final_token", "content": tok})

        emit({"type": "final_stream_start", "content": ""})
        try:
            self.llm.generate(prompt, on_token=on_token)
        except Exception:
            resposta = self.llm.generate(prompt)
            emit({"type": "final_token", "content": resposta})

        resposta = resposta.strip()
        emit({"type": "final", "content": resposta})
        emit({"type": "done", "content": ""})
        self.memory.save_session_with_llm(task, resposta[:200], [], self.llm, self.session_id)
        log.info("MODO CONVERSA: %s → %s chars", task[:50], len(resposta))
        return resposta

    # -----------------------------------------------------------------
    # Entrada principal
    # -----------------------------------------------------------------
    def run(self, task: str, max_steps: int = 0, step_callback=None) -> str:
        if self._cancel.is_set():
            return "Cancelado."

        if self._is_conversational(task):
            return self._run_conversational(task, step_callback)

        if self._needs_collaboration(task):
            return self._run_collaborative(task, step_callback)
        return self._run_single(task, step_callback)
