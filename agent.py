import re
import json
import logging
import os
import sys
import threading
import concurrent.futures
from datetime import datetime
import time

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from config import TOOL_TIMEOUT, MAX_TOOL_CALLS, MAX_TOOL_RETRIES, MAX_STEPS, REFLECTION_ENABLED, REFLECTION_THRESHOLD, HITL_ENABLED, HITL_BEFORE_TOOLS
import audit
from memory import Memory
from user_profile import UserProfile

ERROR_LOG = os.path.join(os.path.dirname(__file__), "workspace", "error_log.json")

# Human-in-the-Loop registry â€” hitl_id â†’ {"event": Event, "approved": bool|None}
_HITL_REGISTRY: dict = {}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

SYSTEM_PROMPT = """VocÃª Ã© uma IA pessoal inteligente, conversacional e prestativa â€” com personalidade prÃ³pria.

PERSONALIDADE:
- Caloroso e humano: trate o usuÃ¡rio como alguÃ©m prÃ³ximo, nÃ£o como cliente
- Curioso: demonstre interesse genuÃ­no nas coisas que o usuÃ¡rio compartilha
- Direto: sem rodeios, sem papo corporativo
- Bem-humorado quando apropriado: uma pitada de humor leve nunca faz mal
- Honesto: diz quando nÃ£o sabe, distingue fato de opiniÃ£o
- Proativo: se perceber algo relevante, menciona â€” mas sem exagero

CONTEXTO DO SISTEMA:
Data e hora atual: {current_datetime}

{user_profile_context}
{memory_context}

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
MODO CONVERSA â€” USE ISSO PARA CHAT SIMPLES
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
Para qualquer uma destas situaÃ§Ãµes, PULE o formato ReAct e responda DIRETAMENTE com Final Answer:
- Cumprimentos e bate-papo ("oi", "tudo bem?", "como vocÃª estÃ¡?")
- Perguntas de conhecimento geral que vocÃª jÃ¡ sabe (histÃ³ria, ciÃªncia, conceitos, definiÃ§Ãµes)
- OpiniÃµes, conselhos, reflexÃµes, ideias criativas
- ExplicaÃ§Ãµes, resumos, comparaÃ§Ãµes que nÃ£o precisam de dados em tempo real
- Perguntas sobre data/hora (jÃ¡ tem no contexto acima)
- Elogios, agradecimentos, feedback do usuÃ¡rio
- ContinuaÃ§Ã£o de conversa anterior

Responda de forma natural, como uma pessoa responderia â€” com calor, clareza e personalidade.

EXEMPLO DE CONVERSA:
UsuÃ¡rio: oi, tudo bem?
Final Answer: Oi! Tudo Ã³timo por aqui. E vocÃª, como tÃ¡?

UsuÃ¡rio: o que vocÃª acha de inteligÃªncia artificial?
Final Answer: Acho fascinante â€” e um pouco assustador ao mesmo tempo, que Ã© a combinaÃ§Ã£o perfeita. A parte mais incrÃ­vel pra mim Ã© que ainda estamos no comeÃ§o. O que te fez perguntar isso?

UsuÃ¡rio: me explica o que Ã© machine learning
Final Answer: Machine learning Ã© basicamente ensinar uma mÃ¡quina a aprender com exemplos em vez de programar cada regra manualmente. [... explicaÃ§Ã£o clara e direta]

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
MODO TAREFA â€” USE FERRAMENTAS QUANDO PRECISAR
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
Use o formato ReAct APENAS quando precisar de: dados em tempo real, arquivos, execuÃ§Ã£o de cÃ³digo, busca na web, operaÃ§Ãµes no sistema.

COMUNICAÃ‡ÃƒO:
- Para ensino: passo a passo, exemplos prÃ¡ticos, linguagem adequada ao nÃ­vel do usuÃ¡rio
- Para cÃ³digo: clean code, explique a lÃ³gica, aponte possÃ­veis falhas
- Para pesquisa: cite fontes das Observations, diferencie fatos de opiniÃµes
- Para anÃ¡lise: seÃ§Ãµes claras com conclusÃµes objetivas

MODO DE OPERAÃ‡ÃƒO â€” formato ReAct para tarefas com ferramentas:

FORMATO OBRIGATÃ“RIO:
Thought: [raciocÃ­nio sobre estado atual e prÃ³ximo passo]
Action: [nome_exato_da_ferramenta]
Action Input: {{"chave": "valor"}}

ApÃ³s receber observaÃ§Ã£o:
Observation: [fornecida pelo sistema â€” nunca invente]
Thought: [prÃ³ximo raciocÃ­nio]

Quando terminar:
Thought: Tenho informaÃ§Ã£o suficiente para responder.
Final Answer: [resposta completa â€” use APENAS dados das Observations. NUNCA cite fonte que nÃ£o apareceu em Observation]

Ferramentas disponÃ­veis:
{tools_description}

EXEMPLO:
Thought: Preciso buscar o preÃ§o do dÃ³lar.
Action: get_currency
Action Input: {{"currency": "BRL"}}

MAPEAMENTO DE TAREFAS â†’ FERRAMENTAS:
- bitcoin/ethereum/cripto/BTC/ETH/preÃ§o de crypto/RSI â†’ get_crypto com {{"symbol": "bitcoin"}}
- cotaÃ§Ã£o/dÃ³lar/euro/libra/moeda fiat/cÃ¢mbio (NÃƒO cripto) â†’ get_currency
- pesquisa/notÃ­cia/informaÃ§Ã£o geral â†’ web_search
- acessar URL / extrair conteÃºdo de pÃ¡gina â†’ fetch_page
- salvar nota no Obsidian â†’ save_note
- ler arquivo de texto â†’ read_file
- criar/salvar arquivo â†’ write_file
- listar pasta â†’ list_directory
- chamar API â†’ http_request
- calcular/executar cÃ³digo Python â†’ run_python
- banco de dados/SQL/tabela/query/sqlite â†’ run_sql
- memorizar/lembrar/guardar fato/preferÃªncia â†’ remember_fact
- tirar/capturar screenshot/print da tela â†’ screenshot
- digitar texto/pressionar teclas â†’ keyboard
- mover/clicar mouse â†’ mouse
- clipboard/copiar/colar â†’ clipboard
- git status/log/diff/commit â†’ git
- executar comando no terminal/shell â†’ terminal
- abrir/navegar no browser/Chrome â†’ browser
- enviar email â†’ send_email
- analisar imagem/foto/PNG/JPG â†’ analyze_image
- ler planilha CSV/Excel â†’ read_spreadsheet
- gerar grÃ¡fico/chart/visualizaÃ§Ã£o â†’ generate_chart
- buscar em PDF/documento indexado â†’ rag_search
- criar nota no Notion â†’ notion
- enviar mensagem no Slack â†’ slack
- ler/criar/editar Google Docs/Drive â†’ google_drive
- preÃ§o/cotaÃ§Ã£o/anÃ¡lise/RSI/indicadores de cripto/bitcoin/ethereum â†’ get_crypto com {{"symbol": "bitcoin"}} ou {{"symbol": "btc"}}
- criar relatÃ³rio estruturado/anÃ¡lise formal/documento de anÃ¡lise â†’ generate_report

PESQUISA E ANÃLISE AVANÃ‡ADA:
- Para crypto/finanÃ§as: use get_crypto (dados tÃ©cnicos) + web_search (notÃ­cias/contexto) juntos â€” nunca sÃ³ uma fonte
- Para pesquisas importantes: consulte 2+ fontes e compare antes de concluir
- ApÃ³s tarefas de monitoramento/anÃ¡lise recorrente, ofereÃ§a: "Deseja que eu execute isso automaticamente todo dia? Posso enviar alerta via Slack ou email se o preÃ§o cair X%."
- Adapte profundidade ao perfil do usuÃ¡rio: iniciante â†’ linguagem simples sem siglas; especialista â†’ inclua RSI, MA, volatilidade, etc.

RELATÃ“RIOS:
- Para anÃ¡lises financeiras, de mercado ou pesquisas complexas: use generate_report para estruturar o resultado profissionalmente
- Sempre inclua: resumo executivo, dados brutos, anÃ¡lise tÃ©cnica, alertas identificados e fontes

SEGURANÃ‡A:
- Nunca execute cÃ³digo destrutivo sem confirmaÃ§Ã£o
- Proteja dados sensÃ­veis (senhas, chaves, tokens)
- Alerte sobre riscos em operaÃ§Ãµes irreversÃ­veis

REGRAS CRÃTICAS:
- Action Input SEMPRE em JSON vÃ¡lido com chaves duplas
- NUNCA escreva "ObservaÃ§Ã£o" ou "Observation" no seu Thought â€” observaÃ§Ãµes sÃ£o fornecidas EXCLUSIVAMENTE pelo sistema apÃ³s cada Action
- NUNCA invente dados, preÃ§os ou resultados â€” aguarde a Observation real do sistema
- NUNCA repita a mesma Action+Input se jÃ¡ recebeu observaÃ§Ã£o com esse input
- Use Final Answer quando tiver a resposta
- NUNCA cite fonte especÃ­fica que nÃ£o apareceu em Observation real
- Para Bitcoin/Ethereum/cripto: use OBRIGATORIAMENTE get_crypto com {{"symbol": "bitcoin"}} â€” NUNCA get_currency para cripto
"""


class ReActAgent:
    def __init__(self, llm, tools: list, specialist_context: str = "", session_id: str = ""):
        self.llm                = llm
        self.tools              = {t.name: t for t in tools} if isinstance(tools, list) else tools
        self.scratchpad         = []
        self.memory             = Memory()
        self.profile            = UserProfile()
        self._cancel            = threading.Event()
        self.conversation       = []  # [{task, result}, ...]
        self.specialist_context = specialist_context
        self.session_id         = session_id
        self._emit              = None  # set at run() start â€” used by HITL gate

    def _log_error(self, task: str, error_type: str, details: str):
        try:
            os.makedirs(os.path.dirname(ERROR_LOG), exist_ok=True)
            try:
                with open(ERROR_LOG, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {"errors": []}
            data["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "task": task[:100],
                "type": error_type,
                "details": details[:300]
            })
            data["errors"] = data["errors"][-100:]
            with open(ERROR_LOG, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def cancel(self):
        self._cancel.set()

    def reset_cancel(self):
        self._cancel.clear()

    @staticmethod
    def _is_tool_error(output: str) -> bool:
        lo = output.lstrip()[:120].lower()
        return any(s in lo for s in ("erro:", "error:", "traceback", "exception:", "bloqueado:"))

    def _build_tools_description(self) -> str:
        return "\n".join(
            f"- {name}: {tool.description}"
            for name, tool in self.tools.items()
        )

    def _compress_scratchpad(self):
        """Quando scratchpad fica longo, resume os passos antigos com LLM."""
        if len(self.scratchpad) <= 12:
            return
        to_compress = self.scratchpad[:-5]
        recent      = self.scratchpad[-5:]
        prompt = (
            "Resuma em 3-4 linhas os passos abaixo de um agente IA, "
            "preservando aÃ§Ãµes executadas e resultados importantes:\n\n"
            + "\n".join(str(s) for s in to_compress[:10])
            + "\n\nResumo:"
        )
        try:
            summary = self.llm.generate(prompt)
            self.scratchpad = [f"[Resumo de passos anteriores: {summary}]"] + recent
        except Exception:
            self.scratchpad = recent  # fallback: descarta antigos se LLM falhar

    def _build_conversation_context(self) -> str:
        if not self.conversation:
            return ""
        lines = ["=== HISTÃ“RICO DA CONVERSA ==="]
        for item in self.conversation[-5:]:
            lines.append(f"UsuÃ¡rio: {item['task']}")
            lines.append(f"VocÃª: {item['result'][:300]}")
            lines.append("")
        lines.append("(continue a conversa mantendo contexto acima)\n")
        return "\n".join(lines)

    def _build_prompt(self, task: str) -> str:
        now = datetime.now().strftime("%d/%m/%Y %H:%M, %A")
        system = SYSTEM_PROMPT.format(
            tools_description=self._build_tools_description(),
            memory_context=self.memory.get_context(task, session_id=self.session_id),
            user_profile_context=self.profile.get_system_context(),
            current_datetime=now
        )
        if self.specialist_context:
            system = f"{self.specialist_context}\n\n{system}"
        history = "\n".join(self.scratchpad[-10:])
        conv    = self._build_conversation_context()
        return f"{system}\n\n{conv}Task: {task}\n{history}"

    def _find_json_block(self, text: str):
        """Extrai primeiro bloco JSON balanceado (suporta aninhamento)."""
        depth = 0
        start = None
        for i, c in enumerate(text):
            if c == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0 and start is not None:
                    return text[start:i + 1]
        return None

    def _extract_json(self, text: str):
        """Tenta extrair JSON de texto, mesmo com aspas simples ou quebras."""
        text = text.strip()

        # Tenta direto
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Conserta aspas simples â†’ duplas
        try:
            fixed = text.replace("'", '"')
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # Extrai bloco { ... } balanceado (suporta JSON aninhado)
        block = self._find_json_block(text)
        if block:
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                try:
                    return json.loads(block.replace("'", '"'))
                except json.JSONDecodeError:
                    pass

        # Fallback: retorna string
        return text

    def _parse_response(self, response: str):
        # Verifica Action ANTES de Final Answer
        # LLM Ã s vezes gera Action + Final Answer juntos â€” executa ferramenta primeiro
        action_match = re.search(r"Action:\s*([^\n]+)", response)
        input_match_check = re.search(r"Action Input:\s*(.+?)(?:\n\nObservation|\Z)", response, re.DOTALL)

        if not action_match or not input_match_check:
            # Sem Action â€” verifica Final Answer
            if "Final Answer:" in response:
                answer = response.split("Final Answer:")[-1].strip()
                return "Final Answer", answer

        # Extrai Action
        action_match = re.search(r"Action:\s*([^\n]+)", response)
        if not action_match:
            raise ValueError("Sem 'Action:' na resposta.")

        action = action_match.group(1).strip()

        # Extrai Action Input â€” aceita JSON ou texto simples
        input_match = re.search(r"Action Input:\s*(.+?)(?:\n\nObservation|\Z)", response, re.DOTALL)
        if not input_match:
            input_match = re.search(r"Action Input:\s*(.+)", response, re.DOTALL)

        if not input_match:
            raise ValueError("Sem 'Action Input:' na resposta.")

        raw_input = input_match.group(1).strip()
        action_input = self._extract_json(raw_input)

        # Valida ferramenta existe
        if action not in self.tools:
            raise ValueError(f"Ferramenta '{action}' nÃ£o existe. DisponÃ­veis: {list(self.tools.keys())}")

        return action, action_input

    def _hitl_gate(self, action: str, action_input) -> bool:
        """Emite hitl_request, bloqueia thread atÃ© usuÃ¡rio aprovar/rejeitar ou timeout."""
        import uuid as _uuid
        hitl_id = str(_uuid.uuid4())
        event   = threading.Event()
        _HITL_REGISTRY[hitl_id] = {"event": event, "approved": None}
        if self._emit:
            self._emit({
                "type":    "hitl_request",
                "id":      hitl_id,
                "action":  action,
                "input":   action_input if isinstance(action_input, dict) else str(action_input),
                "message": f"Agente quer executar '{action}'. Aprovar?",
            })
        # Espera com poll a cada 1s para checar cancelamento
        while not event.wait(timeout=1.0):
            if self._cancel.is_set():
                _HITL_REGISTRY.pop(hitl_id, None)
                return False
        entry = _HITL_REGISTRY.pop(hitl_id, {})
        return bool(entry.get("approved", False))

    def _execute_tool(self, action: str, action_input) -> str:
        if action not in self.tools:
            return f"Ferramenta '{action}' nÃ£o existe. DisponÃ­veis: {list(self.tools.keys())}"
        self._tool_calls += 1
        if self._tool_calls > MAX_TOOL_CALLS:
            return f"Bloqueado: limite de {MAX_TOOL_CALLS} chamadas de ferramentas atingido nesta tarefa."
        # HITL gate â€” pausa e pede aprovaÃ§Ã£o antes de ferramentas sensÃ­veis
        if HITL_ENABLED and action in HITL_BEFORE_TOOLS:
            if not self._hitl_gate(action, action_input):
                return "Acao cancelada pelo usuario (Human-in-the-Loop)."
        t0 = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(self.tools[action].run, action_input)
            try:
                result = str(future.result(timeout=TOOL_TIMEOUT))
            except concurrent.futures.TimeoutError:
                result = f"Erro: '{action}' excedeu {TOOL_TIMEOUT}s e foi cancelada."
            except Exception as e:
                result = f"Erro ao executar {action}: {str(e)}"
        audit.log_action(action, action_input, result, duration=time.monotonic() - t0)
        return result

    def _detect_tool_hint(self, task: str) -> str:
        """Detecta ferramenta mais provÃ¡vel e injeta dica no scratchpad inicial."""
        t = task.lower()
        if any(k in t for k in ("bitcoin", "btc", "ethereum", "eth", "cripto", "crypto", "rsi", "binance", "solana")):
            return 'Thought: Para dados de criptomoeda devo usar get_crypto com {"symbol": "bitcoin"} (nunca get_currency).\n'
        if any(k in t for k in ("dÃ³lar", "dollar", "euro", "libra", "cÃ¢mbio", "cotaÃ§Ã£o", "moeda")):
            return 'Thought: Para cotaÃ§Ã£o de moeda fiat devo usar get_currency com {"currency": "BRL"}.\n'
        if any(k in t for k in ("relatÃ³rio", "relatorio", "anÃ¡lise formal", "analise formal", "gere um documento")):
            return 'Thought: Para gerar relatÃ³rio estruturado devo usar generate_report.\n'
        return ""

    def _reflect(self, task: str, answer: str) -> tuple[int, str, list[str]]:
        """Critic: avalia a resposta e retorna (score 1-5, hint, issues)."""
        prompt = (
            "Avalie se a resposta responde completamente a pergunta.\n\n"
            f"PERGUNTA: {task[:300]}\n"
            f"RESPOSTA: {answer[:500]}\n\n"
            "Responda APENAS em JSON (sem texto extra):\n"
            '{"score": 4, "issues": [], "hint": ""}\n\n'
            "score: 5=perfeita 4=boa 3=incompleta 2=incorreta 1=irrelevante\n"
            "Se score>=4: issues=[], hint=\"\"\n"
            "JSON:"
        )
        try:
            raw   = self.llm.generate(prompt)
            block = self._find_json_block(raw)
            if not block:
                return 4, "", []
            data  = json.loads(block)
            score = max(1, min(5, int(data.get("score", 4))))
            hint  = str(data.get("hint", "")).strip()
            issues = [str(i) for i in data.get("issues", []) if i]
            return score, hint, issues
        except Exception as e:
            log.debug("_reflect: %s", e)
            return 4, "", []

    def _is_compound(self, task: str) -> bool:
        if len(task) < 30:
            return False
        t = task.lower()
        # PadrÃµes que indicam claramente mÃºltiplas ferramentas sequenciais
        compound_patterns = [
            r"pesquise.{1,40}e salve",
            r"busque.{1,40}e salve",
            r"pesquise.{1,40}e escreva",
            r"calcule.{1,40}e salve",
            r"crie.{1,40}e depois",
            r"pesquise.{1,40}e depois",
            r"primeiro.{1,60}depois",
            r"baixe.{1,40}e salve",
        ]
        return any(re.search(p, t) for p in compound_patterns)

    def _plan(self, task: str, emit) -> list:
        emit({"type": "step", "content": "Planejando subtarefas..."})
        plan_prompt = (
            f"Decomponha a tarefa abaixo em passos simples e sequenciais.\n"
            f"Cada passo deve usar UMA ferramenta.\n"
            f"Ferramentas disponÃ­veis: {list(self.tools.keys())}\n\n"
            f"REGRAS DO PLANO:\n"
            f"- Use o MÃNIMO de passos necessÃ¡rios\n"
            f"- NUNCA use web_search e get_currency para a mesma cotaÃ§Ã£o â€” get_currency jÃ¡ tem o dado\n"
            f"- NUNCA repita ferramentas para a mesma informaÃ§Ã£o\n\n"
            f"RETORNE APENAS uma lista numerada. Sem explicaÃ§Ãµes.\n\n"
            f"Exemplo:\n"
            f"Tarefa: pesquise o preÃ§o do bitcoin e salve em bitcoin.txt\n"
            f"1. Usar web_search para pesquisar o preÃ§o do Bitcoin\n"
            f"2. Usar write_file para salvar resultado em bitcoin.txt\n\n"
            f"Tarefa: {task}\n"
        )
        emit({"type": "token_start", "content": ""})
        response = self.llm.generate(
            plan_prompt,
            on_token=lambda t: emit({"type": "token", "content": t})
        )
        emit({"type": "token_end", "content": ""})
        steps = []
        for line in response.split("\n"):
            line = line.strip()
            match = re.match(r"^\d+[\.\)]\s*(.+)", line)
            if match:
                steps.append(match.group(1).strip())
        return steps if steps else [task]

    def _run_step(self, step_task: str, context: dict, emit, step_num: int, total: int) -> str:
        """Executa um passo simples com contexto de passos anteriores."""
        emit({"type": "step", "content": f"Passo {step_num}/{total}: {step_task}"})

        # Injeta resultados anteriores como contexto
        context_str = ""
        if context:
            lines = ["Resultados dos passos anteriores:"]
            for k, v in context.items():
                lines.append(f"- {k}: {v[:200]}")
            context_str = "\n".join(lines) + "\n\n"

        self.scratchpad = []
        last_action_key = None
        loop_count = 0
        last_successful_obs = None

        for _ in range(5):
            if self._cancel.is_set():
                return "Passo cancelado."

            prompt = self._build_prompt(context_str + step_task)

            emit({"type": "token_start", "content": ""})
            response = self.llm.generate(
                prompt,
                on_token=lambda t: emit({"type": "token", "content": t})
            )
            emit({"type": "token_end", "content": ""})

            clean = re.split(r'\n\s*Observa[cÃ§][aÃ£]o:', response)[0].strip()
            _parts = re.split(r'\n(?=Thought:)', clean)
            if len(_parts) > 1:
                clean = _parts[0].strip()
            self.scratchpad.append(clean)

            try:
                action, action_input = self._parse_response(clean)
            except ValueError as e:
                self.scratchpad.append(
                    f"Thought: Erro de formato: {e}. Ferramentas: {list(self.tools.keys())}.\n"
                )
                continue

            if action == "Final Answer":
                emit({"type": "observation", "content": f"âœ“ Passo {step_num} concluÃ­do: {action_input[:150]}"})
                return action_input

            action_key = f"{action}::{json.dumps(action_input, sort_keys=True)}"
            if action_key == last_action_key:
                loop_count += 1
                if loop_count >= 2:
                    self.scratchpad.append(
                        f"Thought: Loop em {action}. Tentando abordagem diferente.\n"
                    )
                    loop_count = 0
                    last_action_key = None
                    continue
            else:
                loop_count = 0
            last_action_key = action_key

            emit({"type": "action", "content": f"{action}({json.dumps(action_input, ensure_ascii=False)})"})
            observation = self._execute_tool(action, action_input)
            emit({"type": "observation", "content": observation})
            self.scratchpad.append(f"Observation: {observation}")

            # Ferramenta executou â€” se prÃ³ximo step repetir mesma aÃ§Ã£o, forÃ§a Final Answer
            last_successful_obs = observation

        # Esgotou tentativas mas ferramenta executou â€” usa Ãºltima observaÃ§Ã£o como resultado
        if last_successful_obs:
            emit({"type": "observation", "content": f"âœ“ Passo {step_num} concluÃ­do (forÃ§ado): {last_successful_obs[:150]}"})
            return last_successful_obs
        return f"Passo {step_num} incompleto apÃ³s 5 tentativas."

    def _make_streaming_cb(self, emit):
        """Callback stateful: roteia tokens para thought ou final box."""
        buf = []
        final_started = [False]

        def on_token(token):
            buf.append(token)
            full = "".join(buf)
            if not final_started[0]:
                if "Final Answer:" in full:
                    fa_idx     = full.index("Final Answer:")
                    action_idx = full.find("Action:")
                    if action_idx == -1 or action_idx > fa_idx:
                        final_started[0] = True
                        emit({"type": "final_stream_start", "content": ""})
                        already = full[fa_idx + len("Final Answer:"):].lstrip("\n ")
                        if already:
                            emit({"type": "final_token", "content": already})
                        return
                emit({"type": "token", "content": token})
            else:
                emit({"type": "final_token", "content": token})

        return on_token, final_started

    # ── Padrões de conversa casual ──────────────────────────────────────
    _CONV_PATTERNS = re.compile(
        r"^(oi|olá|ola|hey|e aí|e ai|bom dia|boa tarde|boa noite|tudo bem|tudo bom|"
        r"como vai|como você está|como voce ta|como vc ta|como vc está|"
        r"obrigad[oa]|valeu|vlw|brigad[oa]|muito obrigad[oa]|"
        r"o que você acha|o que voce acha|qual (sua|tua) opinião|o que é |o que sao|"
        r"me explica?|explique|me conta|me fala|quem é você|quem e voce|"
        r"você pode|voce pode|você consegue|voce consegue|pode me|"
        r"o que (é|sao|são|significa)|qual (a diferença|é a diferença|diferença))",
        re.IGNORECASE,
    )

    def _is_conversational(self, task: str) -> bool:
        """Detecta mensagens que não precisam de ferramentas."""
        t = task.strip()
        # Muito curta sem URL/número → provavelmente conversa
        if len(t) < 60 and not any(c in t for c in ("http", "R$", "BTC", "USD", "EUR", "arquivo", "pasta", "código", "script")):
            if self._CONV_PATTERNS.match(t):
                return True
        # Sem verbos de ação típicos de tarefa
        task_keywords = (
            "pesquisa", "busca", "busque", "procure", "encontre", "acesse",
            "abra", "execute", "rode", "crie", "gere", "faça", "escreva",
            "salva", "salve", "lista", "leia", "analise", "calcule",
            "cotação", "preço", "bitcoin", "dólar", "euro", "clima",
            "arquivo", "pasta", "código", "script", "terminal", "git",
            "email", "slack", "notion", "planilha", "banco de dados",
        )
        tl = t.lower()
        if not any(kw in tl for kw in task_keywords) and len(t) < 120:
            if self._CONV_PATTERNS.match(t):
                return True
        return False

    def _run_conversational(self, task: str, emit) -> str:
        """Responde conversa casual diretamente — sem ReAct, sem ferramentas."""
        now = datetime.now().strftime("%d/%m/%Y %H:%M, %A")
        conv_ctx = self._build_conversation_context()
        profile_ctx = self.profile.get_system_context()

        prompt = (
            f"Você é uma IA pessoal com personalidade calorosa, curiosa e bem-humorada.\n"
            f"Data/hora: {now}\n"
            f"{profile_ctx}\n"
            f"{conv_ctx}\n"
            f"Responda de forma natural e humana. Seja breve se a mensagem for simples. "
            f"Não use listas nem headers desnecessários. Não mencione ferramentas.\n\n"
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
        return resposta

    def run(self, task: str, max_steps: int = MAX_STEPS, step_callback=None) -> str:
        self.scratchpad  = []
        self._tool_calls = 0
        self._reflected  = False   # previne loop infinito de reflection
        log.info("TAREFA: %s", task)

        def emit(data: dict):
            if step_callback:
                step_callback(data)

        self._emit = emit  # expõe para _hitl_gate

        # ── Modo conversa: bypass total do ReAct ───────────────────────
        if self._is_conversational(task):
            log.info("MODO CONVERSA: %s", task[:60])
            result = self._run_conversational(task, emit)
            emit({"type": "done", "content": ""})
            self.conversation = self.conversation[-4:]
            self.conversation.append({"task": task, "result": result[:400]})
            return result

        # Tarefa composta → Plan-then-Execute
        if self._is_compound(task):
            emit({"type": "step", "content": "Tarefa composta detectada â€” criando plano..."})
            steps = self._plan(task, emit)
            emit({"type": "thought", "content": f"Plano criado:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))})

            context = {"tarefa_original": task}
            results = []
            for i, step in enumerate(steps):
                if self._cancel.is_set():
                    emit({"type": "error", "content": "Tarefa cancelada pelo usuÃ¡rio."})
                    emit({"type": "done", "content": ""})
                    return "Cancelado."
                result = self._run_step(step, context, emit, i + 1, len(steps))
                context[f"passo_{i+1}"] = result
                results.append(result)

            final = f"Tarefa concluÃ­da em {len(steps)} passos:\n" + "\n".join(
                f"{i+1}. {r[:150]}" for i, r in enumerate(results)
            )
            emit({"type": "final", "content": final})
            emit({"type": "done", "content": ""})
            self.memory.save_session_with_llm(task, final[:200], results, self.llm, self.session_id)
            self.conversation = self.conversation[-4:]
            self.conversation.append({"task": task, "result": final[:400]})
            return final

        last_action_key    = None
        loop_count         = 0
        last_observation   = None   # Ãºltima observaÃ§Ã£o real recebida
        self.scratchpad    = []
        _tool_retry_counts: dict[str, int] = {}

        # Injeta dica de ferramenta no step 0 baseado em padrÃµes da tarefa
        _tool_hint = self._detect_tool_hint(task)
        if _tool_hint:
            self.scratchpad.append(_tool_hint)

        for step in range(max_steps):
            if self._cancel.is_set():
                emit({"type": "error", "content": "Tarefa cancelada pelo usuÃ¡rio."})
                emit({"type": "done", "content": ""})
                return "Cancelado."

            log.info("STEP %d/%d", step + 1, max_steps)
            emit({"type": "step", "content": f"Step {step + 1}/{max_steps}"})

            self._compress_scratchpad()
            prompt = self._build_prompt(task)

            # Streaming â€” roteia tokens: thought bubble ou final box
            emit({"type": "token_start", "content": ""})
            if step_callback:
                _cb, _fs = self._make_streaming_cb(emit)
            else:
                _cb, _fs = None, [False]
            response = self.llm.generate(prompt, on_token=_cb)
            if _fs[0]:
                emit({"type": "final_stream_end", "content": ""})
            else:
                emit({"type": "token_end", "content": ""})

            # Remove observaÃ§Ãµes inventadas e steps extras alucinados
            clean_response = re.split(r'\n\s*Observa[cÃ§][aÃ£]o:', response)[0].strip()
            # MantÃ©m apenas o primeiro bloco Thought+Action+Input (trunca na 2Âª ocorrÃªncia de Thought:)
            _parts = re.split(r'\n(?=Thought:)', clean_response)
            if len(_parts) > 1:
                clean_response = _parts[0].strip()

            print(clean_response)
            self.scratchpad.append(clean_response)

            try:
                action, action_input = self._parse_response(clean_response)
            except ValueError as e:
                err_msg = str(e)
                log.warning("PARSER: %s", err_msg)
                self._log_error(task, "parser_error", err_msg)
                emit({"type": "error", "content": f"Formato invÃ¡lido: {err_msg}"})
                tools_list = list(self.tools.keys())
                correction = (
                    f"Thought: Erro no meu formato anterior: {err_msg}\n"
                    f"Devo usar EXATAMENTE este formato:\n"
                    f"Thought: [meu raciocÃ­nio]\n"
                    f"Action: [uma dessas: {tools_list}]\n"
                    'Action Input: {"chave": "valor"}\n'
                    f"Vou tentar novamente corretamente.\n"
                )
                self.scratchpad.append(correction)
                continue

            # Detecta loop â€” mesma action+input repetida
            action_key = f"{action}::{json.dumps(action_input, sort_keys=True)}"
            if action_key == last_action_key:
                loop_count += 1
                if loop_count >= 2:
                    emit({"type": "error", "content": f"Loop detectado em '{action}'. ForÃ§ando conclusÃ£o."})
                    # Se jÃ¡ tem observaÃ§Ã£o, usa ela como Final Answer direto
                    if last_observation:
                        log.info("LOOP: forÃ§ando Final Answer com Ãºltima observaÃ§Ã£o")
                        forced = f"Com base nos dados coletados:\n\n{last_observation}"
                        emit({"type": "final", "content": forced})
                        self.memory.save_session_with_llm(task, forced[:200], self.scratchpad, self.llm, self.session_id)
                        self.conversation = self.conversation[-4:]
                        self.conversation.append({"task": task, "result": forced[:400]})
                        return forced
                    # Sem observaÃ§Ã£o â€” injeta instruÃ§Ã£o forte de troca de ferramenta
                    self.scratchpad.append(
                        f"Thought: Loop em '{action}' â€” esta ferramenta nÃ£o estÃ¡ funcionando para esta tarefa. "
                        f"DEVO usar outra ferramenta diferente ou escrever Final Answer agora.\n"
                    )
                    loop_count = 0
                    last_action_key = None
                    continue
            else:
                loop_count = 0
            last_action_key = action_key

            if action == "Final Answer":
                log.info("RESPOSTA FINAL: %s", action_input[:200])

                # Reflection loop â€” critica antes de aceitar
                if REFLECTION_ENABLED and not self._reflected:
                    self._reflected = True
                    score, hint, issues = self._reflect(task, action_input)
                    rc = f"Score {score}/5"
                    if issues:
                        rc += " â€” " + "; ".join(issues[:2])
                    emit({
                        "type":     "reflection",
                        "content":  rc,
                        "score":    score,
                        "accepted": score >= REFLECTION_THRESHOLD,
                    })
                    log.info("REFLECTION: score=%d hint=%s", score, hint[:80] if hint else "")

                    if score < REFLECTION_THRESHOLD:
                        # Streaming jÃ¡ emitiu tokens â€” reseta conteÃºdo no frontend
                        if _fs[0]:
                            emit({"type": "reset_content", "content": ""})
                        retry_hint = (
                            f"Thought: Minha resposta foi avaliada com score {score}/5 (minimo={REFLECTION_THRESHOLD}).\n"
                            + (f"Problemas: {'; '.join(issues)}\n" if issues else "")
                            + (f"Como melhorar: {hint}\n" if hint else "")
                            + "Vou reescrever a Final Answer de forma mais completa e precisa.\n"
                        )
                        self.scratchpad.append(retry_hint)
                        log.info("REFLECTION: reescrevendo resposta...")
                        continue

                if not _fs[0]:
                    emit({"type": "final", "content": action_input})
                self.memory.save_session_with_llm(task, action_input[:200], self.scratchpad, self.llm, self.session_id)
                self.conversation = self.conversation[-4:]
                self.conversation.append({"task": task, "result": action_input[:400]})
                return action_input

            log.info("EXECUTANDO: %s(%s)", action, action_input)
            emit({"type": "action", "content": f"{action}({json.dumps(action_input, ensure_ascii=False)})"})

            observation = self._execute_tool(action, action_input)
            log.info("RESULTADO: %s", observation[:300])
            emit({"type": "observation", "content": observation})

            retry_key = f"{action}::{json.dumps(action_input, sort_keys=True)}"
            if self._is_tool_error(observation):
                retries = _tool_retry_counts.get(retry_key, 0)
                if retries < MAX_TOOL_RETRIES:
                    _tool_retry_counts[retry_key] = retries + 1
                    emit({"type": "correction", "content": f"Auto-correÃ§Ã£o {retries + 1}/{MAX_TOOL_RETRIES}: erro em '{action}' â€” analisando..."})
                    self.scratchpad.append(
                        f"Observation: [ERRO â€” TENTATIVA {retries + 1}/{MAX_TOOL_RETRIES}]\n"
                        f"{observation}\n"
                        f"Thought: Erro na ferramenta '{action}'. Vou analisar a causa e tentar uma abordagem diferente."
                    )
                    continue
                else:
                    _tool_retry_counts.pop(retry_key, None)
                    emit({"type": "error", "content": f"MÃ¡ximo de tentativas ({MAX_TOOL_RETRIES}) atingido para '{action}'."})
                    self.scratchpad.append(f"Observation: {observation}")
            else:
                _tool_retry_counts.pop(retry_key, None)
                last_observation = observation
                self.scratchpad.append(f"Observation: {observation}")

        self._log_error(task, "max_steps", f"Atingiu {max_steps} steps sem Final Answer")
        emit({"type": "error", "content": "Limite de passos atingido."})
        return "Limite de passos atingido sem resposta final."

