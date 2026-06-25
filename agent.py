import re
import json
import logging
import os
import threading
import concurrent.futures
from datetime import datetime
import time
from config import TOOL_TIMEOUT, MAX_TOOL_CALLS
import audit
from memory import Memory

ERROR_LOG = os.path.join(os.path.dirname(__file__), "workspace", "error_log.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um agente autônomo e geral. Resolve qualquer tarefa passo a passo usando ferramentas.

CONTEXTO DO SISTEMA — use direto, sem pesquisar:
Data e hora atual: {current_datetime}
REGRA: Se a tarefa for sobre data/hora/dia, NÃO use ferramentas. Responda DIRETO com Final Answer usando o valor acima.

FORMATO OBRIGATÓRIO — siga exatamente:

Thought: [raciocínio sobre estado atual e próximo passo]
Action: [nome_exato_da_ferramenta]
Action Input: {{"chave": "valor"}}

Após receber observação:

Observation: [fornecida pelo sistema — nunca invente]
Thought: [próximo raciocínio]

Quando terminar:

Thought: Tenho informação suficiente para responder.
Final Answer: [resposta completa — use APENAS dados das Observations. NUNCA cite fonte (Wise, Google, etc.) que não apareceu em uma Observation]

{memory_context}

Ferramentas disponíveis:
{tools_description}

EXEMPLOS DE USO CORRETO:

Exemplo 1 — cotação do dólar em reais:
Thought: Preciso da cotação do dólar em reais. Vou usar get_currency com BRL.
Action: get_currency
Action Input: {{"currency": "BRL"}}

Exemplo 1b — cotação do euro em reais:
Thought: Preciso da cotação do euro em reais. Vou usar get_currency com EUR.
Action: get_currency
Action Input: {{"currency": "EUR"}}

Exemplo 2 — pesquisa geral:
Thought: Preciso pesquisar sobre Python.
Action: web_search
Action Input: {{"query": "Python programming language"}}

Exemplo 3 — ler arquivo:
Thought: Vou ler o arquivo de configuração.
Action: read_file
Action Input: {{"path": "C:/Users/User/Desktop/MEU/IA/teste.txt"}}

Exemplo 4 — executar código:
Thought: Vou calcular isso com Python.
Action: run_python
Action Input: {{"code": "print(sum(range(1, 101)))"}}

Exemplo 5 — query SQL:
Thought: Vou criar uma tabela e inserir dados.
Action: run_sql
Action Input: {{"db": "dados.db", "query": "CREATE TABLE IF NOT EXISTS pessoas (id INTEGER PRIMARY KEY, nome TEXT, idade INTEGER)"}}

MAPEAMENTO DE TAREFAS → FERRAMENTAS:
- cotação/dólar/euro/moeda/câmbio → get_currency

- pesquisa/notícia/informação geral → web_search
- acessar URL / extrair conteúdo de página → fetch_page
- salvar nota no Obsidian → save_note
- ler arquivo → read_file
- criar/salvar arquivo → write_file
- listar pasta → list_directory
- chamar API → http_request
- calcular/executar código → run_python
- banco de dados/SQL/tabela/query/sqlite → run_sql
- memorizar/lembrar/guardar fato/preferência → remember_fact
- tirar/capturar screenshot/print da tela → screenshot
- digitar texto/pressionar teclas no computador → keyboard
- mover/clicar mouse → mouse
- clipboard/área de transferência/copiar/colar → clipboard
- git status/log/diff/commit em repositório → git
- executar comando no terminal/shell → terminal
- abrir/navegar/clicar em browser/Chrome → browser
- enviar email → send_email

REGRAS CRÍTICAS:
- Action Input SEMPRE em JSON válido com chaves duplas
- NUNCA invente observações — aguarde o sistema
- NUNCA repita a mesma Action se já recebeu observação — use o resultado
- Use Final Answer quando tiver a resposta, mesmo que incompleta
- NUNCA cite fonte específica (Wise, Bloomberg, Google, etc.) que não acessou com fetch_page ou web_search — use apenas o que está na Observation
"""


class ReActAgent:
    def __init__(self, llm, tools: list, specialist_context: str = ""):
        self.llm                = llm
        self.tools              = {t.name: t for t in tools} if isinstance(tools, list) else tools
        self.scratchpad         = []
        self.memory             = Memory()
        self._cancel            = threading.Event()
        self.conversation       = []  # [{task, result}, ...]
        self.specialist_context = specialist_context

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
        lines = ["=== TAREFAS RECENTES ==="]
        for item in self.conversation[-3:]:
            lines.append(f"Tarefa: {item['task']}")
            lines.append(f"Resultado: {item['result'][:250]}")
            lines.append("")
        lines.append("========================\n")
        return "\n".join(lines)

    def _build_prompt(self, task: str) -> str:
        now = datetime.now().strftime("%d/%m/%Y %H:%M, %A")
        system = SYSTEM_PROMPT.format(
            tools_description=self._build_tools_description(),
            memory_context=self.memory.get_context(task),
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

        # Conserta aspas simples → duplas
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

        return action, action_input

    def _execute_tool(self, action: str, action_input) -> str:
        if action not in self.tools:
            return f"Ferramenta '{action}' não existe. Disponíveis: {list(self.tools.keys())}"
        self._tool_calls += 1
        if self._tool_calls > MAX_TOOL_CALLS:
            return f"Bloqueado: limite de {MAX_TOOL_CALLS} chamadas de ferramentas atingido nesta tarefa."
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

    def _is_compound(self, task: str) -> bool:
        # Fast-path: tarefa curta ou sem indicadores de sequência → não é composta
        t = task.lower()
        seq_indicators = [" e ", " depois", " então", " em seguida", " salve", " crie", " escreva", " liste", " execute"]
        if len(task) < 20 or not any(kw in t for kw in seq_indicators):
            return False

        prompt = (
            'Responda APENAS "SIM" ou "NÃO":\n'
            "A tarefa abaixo requer múltiplos passos sequenciais usando ferramentas diferentes?\n\n"
            f"Tarefa: {task}\n"
            "Resposta:"
        )
        response = self.llm.generate(prompt).strip().upper()
        return "SIM" in response

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
            self.scratchpad.append(clean)

            try:
                action, action_input = self._parse_response(clean)
            except ValueError as e:
                self.scratchpad.append(
                    f"Thought: Erro de formato: {e}. Ferramentas: {list(self.tools.keys())}.\n"
                )
                continue

            if action == "Final Answer":
                emit({"type": "observation", "content": f"✓ Passo {step_num} concluído: {action_input[:150]}"})
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
            emit({"type": "observation", "content": f"✓ Passo {step_num} concluído (forçado): {last_successful_obs[:150]}"})
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

    def run(self, task: str, max_steps: int = 15, step_callback=None) -> str:
        self.scratchpad  = []
        self._tool_calls = 0
        log.info("TAREFA: %s", task)

        def emit(data: dict):
            if step_callback:
                step_callback(data)

        # Tarefa composta → Plan-then-Execute
        if self._is_compound(task):
            emit({"type": "step", "content": "Tarefa composta detectada — criando plano..."})
            steps = self._plan(task, emit)
            emit({"type": "thought", "content": f"Plano criado:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))})

            context = {"tarefa_original": task}
            results = []
            for i, step in enumerate(steps):
                if self._cancel.is_set():
                    emit({"type": "error", "content": "Tarefa cancelada pelo usuário."})
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
            self.memory.save_session(task, final[:200], results)
            self.conversation = self.conversation[-4:]
            self.conversation.append({"task": task, "result": final[:250]})
            return final

        last_action_key = None
        loop_count      = 0
        self.scratchpad = []

        for step in range(max_steps):
            if self._cancel.is_set():
                emit({"type": "error", "content": "Tarefa cancelada pelo usuário."})
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

            # Remove observações inventadas pelo modelo
            clean_response = re.split(r'\n\s*Observa[cç][aã]o:', response)[0].strip()

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
                    hint = (
                        f"Thought: Estou repetindo {action} com os mesmos parâmetros e não está funcionando. "
                        f"Preciso tentar abordagem diferente ou usar outra ferramenta.\n"
                    )
                    self.scratchpad.append(hint)
                    emit({"type": "error", "content": f"Loop detectado em {action}. Forçando correção."})
                    loop_count = 0
                    last_action_key = None
                    continue
            else:
                loop_count = 0
            last_action_key = action_key

            if action == "Final Answer":
                log.info("RESPOSTA FINAL: %s", action_input[:200])
                if not _fs[0]:
                    emit({"type": "final", "content": action_input})
                self.memory.save_session(task, action_input[:200], self.scratchpad)
                self.conversation = self.conversation[-4:]
                self.conversation.append({"task": task, "result": action_input[:250]})
                return action_input

            log.info("EXECUTANDO: %s(%s)", action, action_input)
            emit({"type": "action", "content": f"{action}({json.dumps(action_input, ensure_ascii=False)})"})

            observation = self._execute_tool(action, action_input)
            log.info("RESULTADO: %s", observation[:300])
            emit({"type": "observation", "content": observation})

            self.scratchpad.append(f"Observation: {observation}")

        self._log_error(task, "max_steps", f"Atingiu {max_steps} steps sem Final Answer")
        emit({"type": "error", "content": "Limite de passos atingido."})
        return "Limite de passos atingido sem resposta final."
