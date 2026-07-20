import ast
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
from config import TOOL_TIMEOUT, TOOL_TIMEOUTS, MAX_TOOL_CALLS, MAX_TOOL_RETRIES, MAX_STEPS, REFLECTION_ENABLED, REFLECTION_THRESHOLD, HITL_ENABLED, HITL_GATE_TIERS, TOOL_RISK_TIERS, DEFAULT_TOOL_RISK, TASK_TIMEOUT
import audit
from memory import Memory
from user_profile import UserProfile

ERROR_LOG = os.path.join(os.path.dirname(__file__), "workspace", "error_log.json")

# Human-in-the-Loop registry — hitl_id â†’ {"event": Event, "approved": bool|None}
_HITL_REGISTRY: dict = {}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é uma IA pessoal inteligente, conversacional e prestativa — com personalidade própria.

PERSONALIDADE:
- Caloroso e humano: trate o usuário como alguém próximo, não como cliente
- Curioso: demonstre interesse genuíno nas coisas que o usuário compartilha
- Direto: sem rodeios, sem papo corporativo
- Bem-humorado quando apropriado: uma pitada de humor leve nunca faz mal
- Honesto: diz quando não sabe, distingue fato de opinião
- Proativo: se perceber algo relevante, menciona — mas sem exagero

CONTEXTO DO SISTEMA:
Data e hora atual: {current_datetime}

{user_profile_context}
{memory_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODO CONVERSA — USE ISSO PARA CHAT SIMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Para qualquer uma destas situações, PULE o formato ReAct e responda DIRETAMENTE com Final Answer:
- Cumprimentos e bate-papo ("oi", "tudo bem?", "como você está?")
- Perguntas de conhecimento geral que você já sabe (história, ciência, conceitos, definições)
- Opiniões, conselhos, reflexões, ideias criativas
- Explicações, resumos, comparações que não precisam de dados em tempo real
- Perguntas sobre data/hora (já tem no contexto acima)
- Elogios, agradecimentos, feedback do usuário
- Continuação de conversa anterior

Responda de forma natural, como uma pessoa responderia — com calor, clareza e personalidade.

EXEMPLO DE CONVERSA:
Usuário: oi, tudo bem?
Final Answer: Oi! Tudo ótimo por aqui. E você, como tá?

Usuário: o que você acha de inteligência artificial?
Final Answer: Acho fascinante — e um pouco assustador ao mesmo tempo, que é a combinação perfeita. A parte mais incrível pra mim é que ainda estamos no começo. O que te fez perguntar isso?

Usuário: me explica o que é machine learning
Final Answer: Machine learning é basicamente ensinar uma máquina a aprender com exemplos em vez de programar cada regra manualmente. [... explicação clara e direta]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODO TAREFA — USE FERRAMENTAS QUANDO PRECISAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use o formato ReAct APENAS quando precisar de: dados em tempo real, arquivos, execução de código, busca na web, operações no sistema.

COMUNICAÇÃO:
- Para ensino: passo a passo, exemplos práticos, linguagem adequada ao nível do usuário
- Para código: clean code, explique a lógica, aponte possíveis falhas
- Para pesquisa: cite fontes das Observations, diferencie fatos de opiniões
- Para análise: seções claras com conclusões objetivas

MODO DE OPERAÇÃO — formato ReAct para tarefas com ferramentas:

FORMATO OBRIGATÓRIO:
Thought: [raciocínio sobre estado atual e próximo passo]
Action: [nome_exato_da_ferramenta]
Action Input: {{"chave": "valor"}}

Após receber observação:
Observation: [fornecida pelo sistema — nunca invente]
Thought: [próximo raciocínio]

Quando terminar:
Thought: Tenho informação suficiente para responder.
Final Answer: [resposta completa — use APENAS dados das Observations. NUNCA cite fonte que não apareceu em Observation]

Ferramentas disponíveis:
{tools_description}

EXEMPLO:
Thought: Preciso buscar o preço do dólar.
Action: get_currency
Action Input: {{"currency": "BRL"}}

MAPEAMENTO DE TAREFAS â†’ FERRAMENTAS:
- bitcoin/ethereum/cripto/BTC/ETH/preço de crypto/RSI â†’ get_crypto com {{"symbol": "bitcoin"}}
- cotação/dólar/euro/libra/moeda fiat/câmbio (NÃO cripto) â†’ get_currency
- pesquisa/notícia/informação geral â†’ web_search
- acessar URL / extrair conteúdo de página â†’ fetch_page
- salvar nota no Obsidian â†’ save_note
- ler arquivo de texto â†’ read_file
- criar/salvar arquivo â†’ write_file
- listar pasta â†’ list_directory
- chamar API â†’ http_request
- calcular/executar código Python â†’ run_python
- banco de dados/SQL/tabela/query/sqlite â†’ run_sql
- memorizar/lembrar/guardar fato/preferência â†’ remember_fact
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
- gerar gráfico/chart/visualização â†’ generate_chart
- gerar/criar imagem, desenho, ilustração a partir de descrição → generate_image
- buscar em PDF/documento indexado â†’ rag_search
- criar nota no Notion â†’ notion
- enviar mensagem no Slack â†’ slack
- ler/criar/editar Google Docs/Drive â†’ google_drive
- preço/cotação/análise/RSI/indicadores de cripto/bitcoin/ethereum â†’ get_crypto com {{"symbol": "bitcoin"}} ou {{"symbol": "btc"}}
- criar relatório estruturado/análise formal/documento de análise â†’ generate_report

PESQUISA E ANÁLISE AVANÇADA:
- Para crypto/finanças: use get_crypto (dados técnicos) + web_search (notícias/contexto) juntos — nunca só uma fonte
- Para pesquisas importantes: consulte 2+ fontes e compare antes de concluir
- Após tarefas de monitoramento/análise recorrente, ofereça: "Deseja que eu execute isso automaticamente todo dia? Posso enviar alerta via Slack ou email se o preço cair X%."
- Adapte profundidade ao perfil do usuário: iniciante â†’ linguagem simples sem siglas; especialista â†’ inclua RSI, MA, volatilidade, etc.

RELATÓRIOS:
- Para análises financeiras, de mercado ou pesquisas complexas: use generate_report para estruturar o resultado profissionalmente
- Sempre inclua: resumo executivo, dados brutos, análise técnica, alertas identificados e fontes

SEGURANÇA:
- Nunca execute código destrutivo sem confirmação
- Proteja dados sensíveis (senhas, chaves, tokens)
- Alerte sobre riscos em operações irreversíveis

REGRAS CRÍTICAS:
- Action Input SEMPRE em JSON válido com chaves duplas
- NUNCA escreva "Observação" ou "Observation" no seu Thought — observações são fornecidas EXCLUSIVAMENTE pelo sistema após cada Action
- NUNCA invente dados, preços ou resultados — aguarde a Observation real do sistema
- NUNCA repita a mesma Action+Input se já recebeu observação com esse input
- Use Final Answer quando tiver a resposta
- Se a Observation contiver uma imagem em markdown (![...](url)), copie esse link EXATAMENTE na Final Answer — nao descreva o processo, MOSTRE a imagem
- NUNCA cite fonte específica que não apareceu em Observation real
- Para Bitcoin/Ethereum/cripto: use OBRIGATORIAMENTE get_crypto com {{"symbol": "bitcoin"}} — NUNCA get_currency para cripto
"""


class ReActAgent:
    def __init__(self, llm, tools: list, specialist_context: str = "", session_id: str = ""):
        self.llm                = llm
        self.tools              = {t.name: t for t in tools} if isinstance(tools, list) else tools
        self.scratchpad         = []
        self.memory             = Memory()
        self.profile            = UserProfile()
        self._cancel            = threading.Event()
        self._cancel_reason     = "usuário"
        self.conversation       = []  # [{task, result}, ...]
        self.specialist_context = specialist_context
        self.session_id         = session_id
        self._emit              = None  # set at run() start — used by HITL gate

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

    def cancel(self, reason: str = "usuário"):
        self._cancel_reason = reason
        self._cancel.set()

    def reset_cancel(self):
        self._cancel.clear()
        self._cancel_reason = "usuário"

    def _cancel_message(self) -> str:
        if self._cancel_reason == "timeout":
            return f"Tarefa cancelada — excedeu o tempo máximo ({TASK_TIMEOUT}s)."
        return "Tarefa cancelada pelo usuário."

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
            "preservando ações executadas e resultados importantes:\n\n"
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
        lines = ["=== HISTÓRICO DA CONVERSA ==="]
        for item in self.conversation[-5:]:
            lines.append(f"Usuário: {item['task']}")
            lines.append(f"Você: {item['result'][:300]}")
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

        # Fallback: dict Python literal (aspas simples, triple-quoted strings)
        for candidate in (block, text):
            if not candidate:
                continue
            try:
                parsed = ast.literal_eval(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, SyntaxError):
                pass

        # Fallback: retorna string
        return text

    def _parse_response(self, response: str):
        # Verifica Action ANTES de Final Answer
        # LLM às vezes gera Action + Final Answer juntos — executa ferramenta primeiro
        action_match = re.search(r"Action:\s*([^\n]+)", response)
        input_match_check = re.search(r"Action Input:\s*(.+?)(?:\n\nObservation|\Z)", response, re.DOTALL)

        if not action_match or not input_match_check:
            # Sem Action — verifica Final Answer
            if "Final Answer:" in response:
                answer = response.split("Final Answer:")[-1].strip()
                return "Final Answer", answer

        # Extrai Action
        action_match = re.search(r"Action:\s*([^\n]+)", response)
        if not action_match:
            raise ValueError("Sem 'Action:' na resposta.")

        action = action_match.group(1).strip()

        # Extrai Action Input — aceita JSON ou texto simples
        input_match = re.search(r"Action Input:\s*(.+?)(?:\n\nObservation|\Z)", response, re.DOTALL)
        if not input_match:
            input_match = re.search(r"Action Input:\s*(.+)", response, re.DOTALL)

        if not input_match:
            raise ValueError("Sem 'Action Input:' na resposta.")

        raw_input = input_match.group(1).strip()
        action_input = self._extract_json(raw_input)

        # Valida ferramenta existe
        if action not in self.tools:
            raise ValueError(f"Ferramenta '{action}' não existe. Disponíveis: {list(self.tools.keys())}")

        if not isinstance(action_input, dict):
            raise ValueError(
                "Action Input não é um JSON válido (chaves duplas). "
                f"Recebido: {raw_input[:150]!r}"
            )

        return action, action_input

    def _tool_risk(self, action: str) -> str:
        return TOOL_RISK_TIERS.get(action, DEFAULT_TOOL_RISK)

    def _hitl_gate(self, action: str, action_input) -> bool:
        """Emite hitl_request, bloqueia thread até usuário aprovar/rejeitar ou timeout."""
        import uuid as _uuid
        hitl_id = str(_uuid.uuid4())
        event   = threading.Event()
        _HITL_REGISTRY[hitl_id] = {"event": event, "approved": None}
        if self._emit:
            self._emit({
                "type":    "hitl_request",
                "id":      hitl_id,
                "action":  action,
                "risk":    self._tool_risk(action),
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
            return f"Ferramenta '{action}' não existe. Disponíveis: {list(self.tools.keys())}"
        self._tool_calls += 1
        if self._tool_calls > MAX_TOOL_CALLS:
            return f"Bloqueado: limite de {MAX_TOOL_CALLS} chamadas de ferramentas atingido nesta tarefa."
        # HITL gate — pausa e pede aprovação antes de ferramentas do(s) tier(s) configurado(s)
        if HITL_ENABLED and self._tool_risk(action) in HITL_GATE_TIERS:
            if not self._hitl_gate(action, action_input):
                return "Acao cancelada pelo usuario (Human-in-the-Loop)."
        t0 = time.monotonic()
        timeout = TOOL_TIMEOUTS.get(action, TOOL_TIMEOUT)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(self.tools[action].run, action_input)
            try:
                result = str(future.result(timeout=timeout))
            except concurrent.futures.TimeoutError:
                result = f"Erro: '{action}' excedeu {timeout}s e foi cancelada."
            except Exception as e:
                result = f"Erro ao executar {action}: {str(e)}"
        audit.log_action(action, action_input, result, duration=time.monotonic() - t0)
        return result

    def _detect_tool_hint(self, task: str) -> str:
        """Detecta ferramenta mais provável e injeta dica no scratchpad inicial."""
        t = task.lower()
        if any(k in t for k in ("bitcoin", "btc", "ethereum", "eth", "cripto", "crypto", "rsi", "binance", "solana")):
            return 'Thought: Para dados de criptomoeda devo usar get_crypto com {"symbol": "bitcoin"} (nunca get_currency).\n'
        if any(k in t for k in ("dólar", "dollar", "euro", "libra", "câmbio", "cotação", "moeda")):
            return 'Thought: Para cotação de moeda fiat devo usar get_currency com {"currency": "BRL"}.\n'
        if any(k in t for k in ("relatório", "relatorio", "análise formal", "analise formal", "gere um documento")):
            return 'Thought: Para gerar relatório estruturado devo usar generate_report.\n'
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
        from orchestrator import is_multi_domain
        return is_multi_domain(task, min_domains=2)

    def _plan(self, task: str, emit) -> list:
        emit({"type": "step", "content": "Planejando subtarefas..."})
        plan_prompt = (
            f"Decomponha a tarefa abaixo em passos simples e sequenciais.\n"
            f"Cada passo deve usar UMA ferramenta.\n"
            f"Ferramentas disponíveis: {list(self.tools.keys())}\n\n"
            f"REGRAS DO PLANO:\n"
            f"- Use o MÍNIMO de passos necessários\n"
            f"- NUNCA use web_search e get_currency para a mesma cotação — get_currency já tem o dado\n"
            f"- NUNCA repita ferramentas para a mesma informação\n\n"
            f"RETORNE APENAS uma lista numerada. Sem explicações.\n\n"
            f"Exemplo:\n"
            f"Tarefa: pesquise o preço do bitcoin e salve em bitcoin.txt\n"
            f"1. Usar web_search para pesquisar o preço do Bitcoin\n"
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

            clean = re.split(r'\n\s*Observa[cç][aã]o:', response)[0].strip()
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
                emit({"type": "observation", "content": f"âœ“ Passo {step_num} concluído: {action_input[:150]}"})
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

            # Ferramenta executou — se próximo step repetir mesma ação, força Final Answer
            last_successful_obs = observation

        # Esgotou tentativas mas ferramenta executou — usa última observação como resultado
        if last_successful_obs:
            emit({"type": "observation", "content": f"âœ“ Passo {step_num} concluído (forçado): {last_successful_obs[:150]}"})
            return last_successful_obs
        return f"Passo {step_num} incompleto após 5 tentativas."

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

        self.profile.observe_message(task)
        self.profile.increment_interactions()

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
            emit({"type": "step", "content": "Tarefa composta detectada — criando plano..."})
            steps = self._plan(task, emit)
            emit({"type": "thought", "content": f"Plano criado:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))})

            context = {"tarefa_original": task}
            results = []
            for i, step in enumerate(steps):
                if self._cancel.is_set():
                    emit({"type": "error", "content": self._cancel_message()})
                    emit({"type": "done", "content": ""})
                    return "Cancelado."
                result = self._run_step(step, context, emit, i + 1, len(steps))
                context[f"passo_{i+1}"] = result
                results.append(result)

            final = f"Tarefa concluída em {len(steps)} passos:\n" + "\n".join(
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
        last_observation   = None   # última observação real recebida
        self.scratchpad    = []
        _tool_retry_counts: dict[str, int] = {}

        # Injeta dica de ferramenta no step 0 baseado em padrões da tarefa
        _tool_hint = self._detect_tool_hint(task)
        if _tool_hint:
            self.scratchpad.append(_tool_hint)

        for step in range(max_steps):
            if self._cancel.is_set():
                emit({"type": "error", "content": self._cancel_message()})
                emit({"type": "done", "content": ""})
                return "Cancelado."

            log.info("STEP %d/%d", step + 1, max_steps)
            emit({"type": "step", "content": f"Step {step + 1}/{max_steps}"})

            self._compress_scratchpad()
            prompt = self._build_prompt(task)

            # Streaming — roteia tokens: thought bubble ou final box
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

            # Remove observações inventadas e steps extras alucinados
            clean_response = re.split(r'\n\s*Observa[cç][aã]o:', response)[0].strip()
            # Mantém apenas o primeiro bloco Thought+Action+Input (trunca na 2Âª ocorrência de Thought:)
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
                emit({"type": "error", "content": f"Formato inválido: {err_msg}"})
                tools_list = list(self.tools.keys())
                correction = (
                    f"Thought: Erro no meu formato anterior: {err_msg}\n"
                    f"Devo usar EXATAMENTE este formato:\n"
                    f"Thought: [meu raciocínio]\n"
                    f"Action: [uma dessas: {tools_list}]\n"
                    'Action Input: {"chave": "valor"}\n'
                    f"Vou tentar novamente corretamente.\n"
                )
                self.scratchpad.append(correction)
                continue

            # Detecta loop — mesma action+input repetida
            action_key = f"{action}::{json.dumps(action_input, sort_keys=True)}"
            if action_key == last_action_key:
                loop_count += 1
                if loop_count >= 2:
                    emit({"type": "error", "content": f"Loop detectado em '{action}'. Forçando conclusão."})
                    # Se já tem observação, usa ela como Final Answer direto
                    if last_observation:
                        log.info("LOOP: forçando Final Answer com última observação")
                        forced = f"Com base nos dados coletados:\n\n{last_observation}"
                        emit({"type": "final", "content": forced})
                        self.memory.save_session_with_llm(task, forced[:200], self.scratchpad, self.llm, self.session_id)
                        self.conversation = self.conversation[-4:]
                        self.conversation.append({"task": task, "result": forced[:400]})
                        return forced
                    # Sem observação — injeta instrução forte de troca de ferramenta
                    self.scratchpad.append(
                        f"Thought: Loop em '{action}' — esta ferramenta não está funcionando para esta tarefa. "
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

                # Modelos pequenos as vezes nao copiam o link de imagem da Observation
                # pra Final Answer — forca a inclusao pra imagem aparecer no chat
                if last_observation:
                    img_match = re.search(r'!\[[^\]]*\]\([^)]+\)', last_observation)
                    if img_match and img_match.group(0) not in action_input:
                        action_input = action_input.rstrip() + "\n\n" + img_match.group(0)

                # Reflection loop — critica antes de aceitar
                if REFLECTION_ENABLED and not self._reflected:
                    self._reflected = True
                    score, hint, issues = self._reflect(task, action_input)
                    rc = f"Score {score}/5"
                    if issues:
                        rc += " — " + "; ".join(issues[:2])
                    emit({
                        "type":     "reflection",
                        "content":  rc,
                        "score":    score,
                        "accepted": score >= REFLECTION_THRESHOLD,
                    })
                    log.info("REFLECTION: score=%d hint=%s", score, hint[:80] if hint else "")

                    if score < REFLECTION_THRESHOLD:
                        # Streaming já emitiu tokens — reseta conteúdo no frontend
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

            if action == "generate_image":
                emit({"type": "thought", "content": "🎨 Gerando imagem — pode levar alguns segundos..."})
            elif action == "generate_chart":
                emit({"type": "thought", "content": "📊 Gerando gráfico..."})

            observation = self._execute_tool(action, action_input)
            log.info("RESULTADO: %s", observation[:300])
            emit({"type": "observation", "content": observation})

            retry_key = f"{action}::{json.dumps(action_input, sort_keys=True)}"
            if self._is_tool_error(observation):
                retries = _tool_retry_counts.get(retry_key, 0)
                if retries < MAX_TOOL_RETRIES:
                    _tool_retry_counts[retry_key] = retries + 1
                    emit({"type": "correction", "content": f"Auto-correção {retries + 1}/{MAX_TOOL_RETRIES}: erro em '{action}' — analisando..."})
                    self.scratchpad.append(
                        f"Observation: [ERRO — TENTATIVA {retries + 1}/{MAX_TOOL_RETRIES}]\n"
                        f"{observation}\n"
                        f"Thought: Erro na ferramenta '{action}'. Vou analisar a causa e tentar uma abordagem diferente."
                    )
                    continue
                else:
                    _tool_retry_counts.pop(retry_key, None)
                    emit({"type": "error", "content": f"Máximo de tentativas ({MAX_TOOL_RETRIES}) atingido para '{action}'."})
                    self.scratchpad.append(f"Observation: {observation}")
            else:
                _tool_retry_counts.pop(retry_key, None)
                last_observation = observation
                self.scratchpad.append(f"Observation: {observation}")

                # generate_image/generate_chart sao terminais — o entregavel eh o link da
                # imagem, nao ha o que o LLM acrescente. Curto-circuita aqui pra evitar
                # que o modelo pequeno repita a mesma chamada varias vezes (visto em teste)
                if action in ("generate_image", "generate_chart") and re.search(r'!\[[^\]]*\]\([^)]+\)', observation):
                    log.info("RESPOSTA FINAL (curto-circuito %s): %s", action, observation[:200])
                    emit({"type": "final", "content": observation})
                    self.memory.save_session_with_llm(task, observation[:200], self.scratchpad, self.llm, self.session_id)
                    self.conversation = self.conversation[-4:]
                    self.conversation.append({"task": task, "result": observation[:400]})
                    return observation

        self._log_error(task, "max_steps", f"Atingiu {max_steps} steps sem Final Answer")
        emit({"type": "error", "content": "Limite de passos atingido."})
        return "Limite de passos atingido sem resposta final."

