import re
import json
from datetime import datetime
from memory import Memory

SYSTEM_PROMPT = """Você é um agente autônomo e geral. Resolve qualquer tarefa passo a passo usando ferramentas.

CONTEXTO DO SISTEMA — use direto, sem pesquisar:
Data e hora atual: {current_datetime}
Se a tarefa for sobre data/hora, responda imediatamente com Final Answer.

FORMATO OBRIGATÓRIO — siga exatamente:

Thought: [raciocínio sobre estado atual e próximo passo]
Action: [nome_exato_da_ferramenta]
Action Input: {{"chave": "valor"}}

Após receber observação:

Observation: [fornecida pelo sistema — nunca invente]
Thought: [próximo raciocínio]

Quando terminar:

Thought: Tenho informação suficiente para responder.
Final Answer: [resposta completa e detalhada]

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

REGRAS CRÍTICAS:
- Action Input SEMPRE em JSON válido com chaves duplas
- NUNCA invente observações — aguarde o sistema
- NUNCA repita a mesma Action se já recebeu observação — use o resultado
- Use Final Answer quando tiver a resposta, mesmo que incompleta
"""


class ReActAgent:
    def __init__(self, llm, tools: list):
        self.llm     = llm
        self.tools   = {t.name: t for t in tools}
        self.scratchpad = []
        self.memory  = Memory()

    def _build_tools_description(self) -> str:
        return "\n".join(
            f"- {name}: {tool.description}"
            for name, tool in self.tools.items()
        )

    def _build_prompt(self, task: str) -> str:
        now = datetime.now().strftime("%d/%m/%Y %H:%M, %A")
        system = SYSTEM_PROMPT.format(
            tools_description=self._build_tools_description(),
            memory_context=self.memory.get_context(),
            current_datetime=now
        )
        history = "\n".join(self.scratchpad[-10:])
        return f"{system}\n\nTask: {task}\n{history}"

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

        # Extrai primeiro bloco { ... }
        match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                try:
                    return json.loads(match.group().replace("'", '"'))
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
            available = list(self.tools.keys())
            return f"Ferramenta '{action}' não existe. Disponíveis: {available}"
        try:
            return str(self.tools[action].run(action_input))
        except Exception as e:
            return f"Erro ao executar {action}: {str(e)}"

    def _is_compound(self, task: str) -> bool:
        keywords = [
            " e salve", " e depois", " então salve", " em seguida",
            " e escreva", " e crie", " e liste", " e execute",
            " e pesquise", " depois salve", " depois escreva",
        ]
        t = task.lower()
        return any(kw in t for kw in keywords)

    def _plan(self, task: str, emit) -> list:
        emit({"type": "step", "content": "Planejando subtarefas..."})
        plan_prompt = (
            f"Decomponha a tarefa abaixo em passos simples e sequenciais.\n"
            f"Cada passo deve usar UMA ferramenta.\n"
            f"Ferramentas disponíveis: {list(self.tools.keys())}\n\n"
            f"RETORNE APENAS uma lista numerada. Sem explicações.\n\n"
            f"Exemplo:\n"
            f"Tarefa: pesquise o preço do bitcoin e salve em bitcoin.txt\n"
            f"1. Usar web_search para pesquisar o preço do Bitcoin\n"
            f"2. Usar write_file para salvar resultado em bitcoin.txt\n\n"
            f"Tarefa: {task}\n"
        )
        response = self.llm.generate(plan_prompt)
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

    def run(self, task: str, max_steps: int = 15, step_callback=None) -> str:
        self.scratchpad = []
        print(f"\n{'#'*50}")
        print(f"TAREFA: {task}")
        print(f"{'#'*50}")

        def emit(data: dict):
            if step_callback:
                step_callback(data)

        # Tarefa composta → Plan-then-Execute
        if self._is_compound(task):
            emit({"type": "step", "content": "Tarefa composta detectada — criando plano..."})
            steps = self._plan(task, emit)
            emit({"type": "thought", "content": f"Plano criado:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))})

            context = {}
            results = []
            for i, step in enumerate(steps):
                result = self._run_step(step, context, emit, i + 1, len(steps))
                context[f"passo_{i+1}"] = result
                results.append(result)

            final = f"Tarefa concluída em {len(steps)} passos:\n" + "\n".join(
                f"{i+1}. {r[:150]}" for i, r in enumerate(results)
            )
            emit({"type": "final", "content": final})
            emit({"type": "done", "content": ""})
            self.memory.save_session(task, final[:200], [])
            return final

        last_action_key = None
        loop_count      = 0
        self.scratchpad = []

        for step in range(max_steps):
            print(f"\n{'='*40} STEP {step + 1}/{max_steps} {'='*40}")
            emit({"type": "step", "content": f"Step {step + 1}/{max_steps}"})

            prompt = self._build_prompt(task)

            # Streaming — envia tokens ao frontend em tempo real
            emit({"type": "token_start", "content": ""})
            response = self.llm.generate(
                prompt,
                on_token=lambda t: emit({"type": "token", "content": t}) if step_callback else None
            )
            emit({"type": "token_end", "content": ""})

            # Remove observações inventadas pelo modelo
            clean_response = re.split(r'\n\s*Observa[cç][aã]o:', response)[0].strip()

            print(clean_response)
            self.scratchpad.append(clean_response)

            try:
                action, action_input = self._parse_response(clean_response)
            except ValueError as e:
                err_msg = str(e)
                print(f"\n[ERRO PARSER]: {err_msg}")
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
                        f"Preciso tentar algo diferente. "
                        f"Para cotação do dólar em reais, o parâmetro correto é currency='BRL', não 'USD'.\n"
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
                print(f"\n{'#'*50}\nRESPOSTA FINAL:\n{action_input}\n{'#'*50}")
                emit({"type": "final", "content": action_input})
                self.memory.save_session(task, action_input[:200], self.scratchpad)
                return action_input

            print(f"\n[EXECUTANDO] {action}({action_input})")
            emit({"type": "action", "content": f"{action}({json.dumps(action_input, ensure_ascii=False)})"})

            observation = self._execute_tool(action, action_input)
            print(f"[RESULTADO] {observation[:300]}{'...' if len(observation) > 300 else ''}")
            emit({"type": "observation", "content": observation})

            self.scratchpad.append(f"Observation: {observation}")

        emit({"type": "error", "content": "Limite de passos atingido."})
        return "Limite de passos atingido sem resposta final."
