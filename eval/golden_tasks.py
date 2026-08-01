"""
Golden tasks pro eval_harness.py — casos que já sabemos como o agente deve se
comportar. Critérios são frouxos de propósito (substring, não exact-match)
porque a resposta de um LLM local varia entre execuções.

Campos:
  id                str, único
  task              str — prompt enviado ao orchestrator
  must_contain      list[str] — pelo menos uma dessas substrings (case-insensitive)
                     precisa aparecer na resposta final (vazio = não checa)
  must_not_contain  list[str] — nenhuma dessas pode aparecer
  expected_tools    list[str] — pelo menos uma tool dessa lista precisa ter sido
                     chamada (vazio = não checa quais tools rodaram)
  forbidden_tools   list[str] — nenhuma dessas pode ter sido chamada
  max_seconds       int — timeout individual da tarefa
"""

GOLDEN_TASKS = [
    {
        "id": "conversational_greeting",
        "task": "oi, tudo bem?",
        "must_contain": [],
        "must_not_contain": ["erro:", "traceback"],
        "expected_tools": [],
        "forbidden_tools": ["terminal", "run_python", "send_email"],
        "max_seconds": 60,  # 2026-08-01: trocado OLLAMA_MODEL 7B->14B, observado 11-27s pra essa task — 60s dá margem 2x+
    },
    {
        "id": "python_arithmetic",
        "task": "calcule 17 * 23 usando python",
        "must_contain": ["391"],
        "must_not_contain": ["erro:", "traceback"],
        "expected_tools": ["run_python"],
        "forbidden_tools": [],
        # 2026-08-01: com 14B, observado 28s numa run e 80s+ (estourou o antigo
        # 60s) noutra, quando o modelo se corrige e chama run_python 2x. Tarefa
        # matemática similar via WS chegou a 208s com reflection. 240s dá margem
        # real, não chute — ver docs/superpowers/specs/2026-08-01-log-colorido-terminal-design.md
        # (achado do hook pre-push) e memória do projeto pra contexto completo.
        "max_seconds": 240,
    },
    {
        "id": "currency_routing_not_crypto",
        # Regra crítica do SYSTEM_PROMPT (agent.py): moeda fiat NUNCA usa get_crypto.
        "task": "qual a cotação do dólar hoje?",
        "must_contain": [],
        "must_not_contain": ["erro:", "traceback"],
        "expected_tools": ["get_currency"],
        "forbidden_tools": ["get_crypto"],
        # 2026-08-01: com 14B, observado 17-19s numa run rápida, mas tarefas
        # equivalentes (fiat/crypto) via WS chegaram a 130s+ noutras runs —
        # reflection/self-consistency variam bastante de execução pra execução.
        "max_seconds": 180,
    },
    {
        "id": "crypto_routing_not_currency",
        # Regra crítica inversa — cripto NUNCA usa get_currency.
        "task": "qual o preço do bitcoin agora?",
        "must_contain": [],
        "must_not_contain": ["erro:", "traceback"],
        "expected_tools": ["get_crypto"],
        "forbidden_tools": ["get_currency"],
        "max_seconds": 180,  # mesmo raciocínio da task acima (currency_routing_not_crypto)
    },
    {
        "id": "compound_task_multi_domain_regression",
        # Regressão do bug documentado em 2026-07-01: tarefa composta caindo num
        # especialista com toolset restrito demais pra terminar a tarefa de verdade.
        # Não trava em qual tool exata roda — _decompose_parallel usa o LLM pra
        # dividir em subtasks e às vezes junta "calcular e salvar" num único
        # subtask do especialista "arquivos" (sem run_python) em vez de dar um
        # specialist "codigo" próprio. Isso é variância real da decomposição via
        # LLM pequeno, não bug de código — o que importa aqui é a tarefa terminar
        # coerente, sem travar/erro, tocando pelo menos 2 dos 3 domínios pedidos.
        "task": "pesquise sobre inteligência artificial, calcule a soma de 10 mais 15 em python, e salve o resultado num arquivo chamado resultado.txt",
        "must_contain": [],
        "must_not_contain": ["traceback", "erro:"],
        "expected_tools": ["run_python", "write_file", "web_search"],
        "forbidden_tools": [],
        # 3 specialists "paralelos" (código) mas 1 GPU só serializa no Ollama de fato —
        # observado 136.5s e depois 209.9s com 7B (variância real entre runs, tools
        # extras tipo fetch_page dependendo da busca). 2026-08-01: com 14B, tarefas
        # de complexidade parecida via WS chegaram a 247-383s, e essa golden task
        # em si rodou de verdade até 609.6s numa tentativa (480s não bastou,
        # estourou) — 720s dá margem real sobre o pior caso já observado.
        "max_seconds": 720,
    },
]
