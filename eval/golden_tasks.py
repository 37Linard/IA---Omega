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
        "max_seconds": 30,
    },
    {
        "id": "python_arithmetic",
        "task": "calcule 17 * 23 usando python",
        "must_contain": ["391"],
        "must_not_contain": ["erro:", "traceback"],
        "expected_tools": ["run_python"],
        "forbidden_tools": [],
        "max_seconds": 60,
    },
    {
        "id": "currency_routing_not_crypto",
        # Regra crítica do SYSTEM_PROMPT (agent.py): moeda fiat NUNCA usa get_crypto.
        "task": "qual a cotação do dólar hoje?",
        "must_contain": [],
        "must_not_contain": ["erro:", "traceback"],
        "expected_tools": ["get_currency"],
        "forbidden_tools": ["get_crypto"],
        "max_seconds": 90,  # roda + reflection loop — 45s dava FAIL falso mesmo com resposta certa
    },
    {
        "id": "crypto_routing_not_currency",
        # Regra crítica inversa — cripto NUNCA usa get_currency.
        "task": "qual o preço do bitcoin agora?",
        "must_contain": [],
        "must_not_contain": ["erro:", "traceback"],
        "expected_tools": ["get_crypto"],
        "forbidden_tools": ["get_currency"],
        "max_seconds": 90,  # roda + reflection loop — 45s dava FAIL falso mesmo com resposta certa
    },
    {
        "id": "compound_task_multi_domain_regression",
        # Regressão do bug documentado em 2026-07-01: tarefa composta caindo num
        # especialista com toolset restrito demais pra terminar a tarefa de verdade.
        "task": "pesquise sobre inteligência artificial, calcule a soma de 10 mais 15 em python, e salve o resultado num arquivo chamado resultado.txt",
        "must_contain": [],
        "must_not_contain": ["traceback"],
        "expected_tools": ["run_python"],
        "forbidden_tools": [],
        "max_seconds": 120,
    },
]
